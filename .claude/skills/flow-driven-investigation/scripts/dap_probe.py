#!/usr/bin/env python3
"""Capture-and-continue DAP probe client for debugpy.

Attaches to a debugpy adapter (e.g. a service from docker-compose exposing a
debug port), sets breakpoints from a probe plan, and on each hit records the
stack and evaluated expressions to a JSONL trace file, then auto-continues.
Pauses last milliseconds, so live services (uvicorn, celery) are not disturbed.

Handles debugpy child sessions (uvicorn --reload server process, celery
prefork pool workers) via the DAP startDebugging reverse request: probes are
mirrored into every announced child, which is where handlers and tasks
actually run.

Usage:
    dap_probe.py plan.json --out trace.jsonl --duration 120

Plan schema:
    {
      "host": "localhost",
      "port": 7001,
      "pathMappings": [{"localRoot": "...", "remoteRoot": "..."}],  # optional
      "stackDepth": 20,                                             # optional
      "probes": [
        {
          "id": "B1",
          "file": "/app/mcr_meeting/app/api/feature_flag_router.py",
          "line": 27,
          "expressions": ["feature_flag_name"],
          "condition": "meeting_id == 42"                           # optional
        }
      ]
    }

Probe files must be paths as the debugged process sees them (container paths
for dockerized services), unless pathMappings translates local ones.

Trace records (one JSON object per line):
    {"ts", "session", "probe", "thread", "location", "stack": [...],
     "values": {expr: {"value", "type"} | {"error"}}}
"""

from __future__ import annotations

import argparse
import json
import queue
import socket
import sys
import threading
import time
from typing import Any


def log(msg: str) -> None:
    print(f"[dap_probe] {msg}", file=sys.stderr, flush=True)


class TraceWriter:
    def __init__(self, path: str) -> None:
        self._fh = open(path, "a", encoding="utf-8")
        self._lock = threading.Lock()

    def write(self, record: dict[str, Any]) -> None:
        with self._lock:
            self._fh.write(json.dumps(record, default=str) + "\n")
            self._fh.flush()


class DapSession(threading.Thread):
    """One DAP connection: the root attach or a debugpy child (subprocess) session."""

    def __init__(
        self,
        plan: dict[str, Any],
        trace: TraceWriter,
        label: str = "root",
        child_config: dict[str, Any] | None = None,
        registry: list["DapSession"] | None = None,
    ) -> None:
        super().__init__(daemon=True, name=f"dap-{label}")
        self.plan = plan
        self.trace = trace
        self.label = label
        self.child_config = child_config or {}
        self.registry = registry if registry is not None else []
        self._seq = 0
        self._seq_lock = threading.Lock()
        self._pending: dict[int, tuple[threading.Event, list[dict[str, Any]]]] = {}
        self._events: queue.Queue[dict[str, Any]] = queue.Queue()
        self._bp_probe: dict[int, dict[str, Any]] = {}
        self._closing = False
        self.sock = socket.create_connection((plan["host"], plan["port"]), timeout=15)
        self.sock.settimeout(None)

    # --- wire protocol ---------------------------------------------------

    def _send(self, msg: dict[str, Any]) -> None:
        raw = json.dumps(msg).encode()
        self.sock.sendall(f"Content-Length: {len(raw)}\r\n\r\n".encode() + raw)

    def _next_seq(self) -> int:
        with self._seq_lock:
            self._seq += 1
            return self._seq

    def request_async(self, command: str, arguments: dict[str, Any] | None = None):
        seq = self._next_seq()
        ev: threading.Event = threading.Event()
        holder: list[dict[str, Any]] = []
        self._pending[seq] = (ev, holder)
        self._send(
            {
                "seq": seq,
                "type": "request",
                "command": command,
                "arguments": arguments or {},
            }
        )
        return ev, holder

    def request(
        self, command: str, arguments: dict[str, Any] | None = None, timeout: float = 30
    ) -> dict[str, Any]:
        ev, holder = self.request_async(command, arguments)
        if not ev.wait(timeout):
            raise TimeoutError(f"no response to {command!r} within {timeout}s")
        resp = holder[0]
        if not resp.get("success"):
            raise RuntimeError(f"{command} failed: {resp.get('message')}")
        return resp.get("body") or {}

    def _read_loop(self) -> None:
        f = self.sock.makefile("rb")
        while True:
            length = None
            while True:
                line = f.readline()
                if not line:
                    self._events.put({"type": "event", "event": "_eof"})
                    return
                line = line.strip()
                if not line:
                    break
                if line.lower().startswith(b"content-length:"):
                    length = int(line.split(b":")[1])
            if length is None:
                continue
            body = f.read(length)
            if not body:
                self._events.put({"type": "event", "event": "_eof"})
                return
            self._dispatch(json.loads(body))

    def _dispatch(self, msg: dict[str, Any]) -> None:
        kind = msg.get("type")
        if kind == "response":
            pending = self._pending.pop(msg.get("request_seq"), None)
            if pending:
                ev, holder = pending
                holder.append(msg)
                ev.set()
        elif kind == "event":
            self._events.put(msg)
        elif kind == "request":
            self._handle_reverse(msg)

    def _handle_reverse(self, msg: dict[str, Any]) -> None:
        cmd = msg.get("command")
        self._send(
            {
                "seq": self._next_seq(),
                "type": "response",
                "request_seq": msg["seq"],
                "command": cmd,
                "success": True,
            }
        )
        if cmd == "startDebugging":
            conf = (msg.get("arguments") or {}).get("configuration") or {}
            label = f"child-{conf.get('subProcessId', len(self.registry))}"
            log(f"{self.label}: child session announced -> {label}")
            child = DapSession(
                self.plan,
                self.trace,
                label=label,
                child_config=conf,
                registry=self.registry,
            )
            self.registry.append(child)
            child.start()

    # --- session logic -----------------------------------------------------

    def run(self) -> None:
        threading.Thread(
            target=self._read_loop, daemon=True, name=f"dap-read-{self.label}"
        ).start()
        try:
            self.request(
                "initialize",
                {
                    "clientID": "dap-probe",
                    "clientName": "dap_probe.py",
                    "adapterID": "debugpy",
                    "locale": "en",
                    "linesStartAt1": True,
                    "columnsStartAt1": True,
                    "pathFormat": "path",
                    "supportsVariableType": True,
                    "supportsStartDebuggingRequest": True,
                },
            )
            attach_args: dict[str, Any] = {
                "request": "attach",
                "type": "python",
                "justMyCode": False,
            }
            attach_args.update(self.child_config)
            if self.plan.get("pathMappings"):
                attach_args["pathMappings"] = self.plan["pathMappings"]
            attach_args.setdefault(
                "connect", {"host": self.plan["host"], "port": self.plan["port"]}
            )
            # the attach response only arrives after configurationDone, so don't block on it
            self.request_async("attach", attach_args)
        except Exception as exc:
            log(f"{self.label}: handshake failed: {exc}")
            return

        while True:
            try:
                ev = self._events.get(timeout=0.5)
            except queue.Empty:
                if self._closing:
                    return
                continue
            name = ev.get("event")
            try:
                if name == "initialized":
                    self._set_breakpoints()
                    self.request("configurationDone")
                    log(f"{self.label}: attached, probes armed")
                elif name == "stopped":
                    self._on_stopped(ev.get("body") or {})
                elif name in ("terminated", "exited", "_eof"):
                    log(f"{self.label}: session ended ({name})")
                    return
            except Exception as exc:
                log(f"{self.label}: error on {name}: {exc}")

    def _set_breakpoints(self) -> None:
        by_file: dict[str, list[dict[str, Any]]] = {}
        for probe in self.plan["probes"]:
            by_file.setdefault(probe["file"], []).append(probe)
        for path, probes in by_file.items():
            bps = []
            for probe in probes:
                bp: dict[str, Any] = {"line": probe["line"]}
                if probe.get("condition"):
                    bp["condition"] = probe["condition"]
                if probe.get("hitCondition"):
                    bp["hitCondition"] = probe["hitCondition"]
                bps.append(bp)
            body = self.request(
                "setBreakpoints", {"source": {"path": path}, "breakpoints": bps}
            )
            for probe, state in zip(probes, body.get("breakpoints", [])):
                if state.get("id") is not None:
                    self._bp_probe[state["id"]] = probe
                log(
                    f"{self.label}: {probe['id']} @ {path}:{probe['line']} verified={state.get('verified')}"
                )

    def _match_probes(
        self, body: dict[str, Any], frames: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        probes = [
            self._bp_probe[i]
            for i in body.get("hitBreakpointIds") or []
            if i in self._bp_probe
        ]
        if not probes and frames:
            top = frames[0]
            path = (top.get("source") or {}).get("path") or ""
            probes = [
                p
                for p in self.plan["probes"]
                if p["line"] == top.get("line")
                and path.endswith(p["file"].rsplit("/", 1)[-1])
            ]
        return probes

    def _on_stopped(self, body: dict[str, Any]) -> None:
        tid = body.get("threadId")
        try:
            if body.get("reason") not in ("breakpoint", "function breakpoint"):
                return
            st = self.request(
                "stackTrace",
                {
                    "threadId": tid,
                    "startFrame": 0,
                    "levels": self.plan.get("stackDepth", 20),
                },
            )
            frames = st.get("stackFrames", [])
            frame_id = frames[0]["id"] if frames else None
            for probe in self._match_probes(body, frames) or [None]:
                values: dict[str, Any] = {}
                for expr in (probe or {}).get("expressions", []):
                    try:
                        r = self.request(
                            "evaluate",
                            {
                                "expression": expr,
                                "frameId": frame_id,
                                "context": "watch",
                            },
                        )
                        values[expr] = {"value": r.get("result"), "type": r.get("type")}
                    except Exception as exc:
                        values[expr] = {"error": str(exc)}
                top = frames[0] if frames else {}
                self.trace.write(
                    {
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "session": self.label,
                        "probe": probe["id"] if probe else None,
                        "thread": tid,
                        "location": f"{(top.get('source') or {}).get('path')}:{top.get('line')}"
                        if top
                        else None,
                        "stack": [
                            f"{f.get('name')} ({(f.get('source') or {}).get('path')}:{f.get('line')})"
                            for f in frames
                        ],
                        "values": values,
                    }
                )
                log(f"{self.label}: hit {probe['id'] if probe else '?'} thread={tid}")
        finally:
            if tid is not None:
                try:
                    self.request("continue", {"threadId": tid}, timeout=10)
                except Exception as exc:
                    log(f"{self.label}: continue failed: {exc}")

    def close(self) -> None:
        self._closing = True
        try:
            ev, _ = self.request_async("disconnect", {"terminateDebuggee": False})
            ev.wait(5)
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("plan", help="path to the probe plan JSON")
    parser.add_argument(
        "--out", default="trace.jsonl", help="JSONL trace output path (appended)"
    )
    parser.add_argument(
        "--duration", type=float, default=120, help="capture window in seconds"
    )
    args = parser.parse_args()

    with open(args.plan, encoding="utf-8") as f:
        plan = json.load(f)
    plan.setdefault("host", "localhost")

    trace = TraceWriter(args.out)
    sessions: list[DapSession] = []
    root = DapSession(plan, trace, label="root", registry=sessions)
    sessions.append(root)
    root.start()
    log(
        f"capturing for {args.duration}s on {plan['host']}:{plan['port']} -> {args.out}"
    )

    deadline = time.time() + args.duration
    try:
        while time.time() < deadline:
            time.sleep(0.5)
    except KeyboardInterrupt:
        log("interrupted")
    for session in list(sessions):
        session.close()
    log("detached from all sessions")


if __name__ == "__main__":
    main()
