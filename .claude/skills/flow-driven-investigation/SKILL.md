---
name: flow-driven-investigation
description: Locate a bug's root cause by replaying it locally and observing the data flow with a debugger at every component boundary — no guessing, no skipped hops. Use when the user asks to investigate a reproducible bug in the dockerized Python services (mcr-core, mcr-gateway, mcr-generation, mcr-capture-worker) and provides an error (Sentry issue or message/traceback) plus the artifacts and steps to reproduce it locally. Investigation only — it convicts the failing method and proposes hypotheses or a fix but never applies them. Not for non-reproducible or production-only issues, nor frontend bugs.
---

# Flow-driven investigation

Bisect the failure path by observing actual values at every boundary the data crosses, at two zoom levels: first across services/components (zoom 1), then inside the convicted component (zoom 2). The debugger produces every verdict; nothing else may. You do not hunt the cause — it is what the bisection converges to, surfaced only when the failing frame is convicted by captured trace lines.

## The process is a locked sequence of gates

Work them in order. You may not open a gate until the previous gate's **exit artifact** exists. Doing gate N's work during gate N−1 — especially reaching a conclusion before the debugger has spoken — means you did not run this skill, regardless of what the final report shows.

```
G0  Repro            → the failure fires locally, no debugger attached
G1  Coarse map       → zoom-1 boundary table, EVERY verdict = UNKNOWN   (no code-under-investigation executed yet)
G2  Debugger (zoom 1)→ verdicts filled ONLY from trace-line ids; a segment convicted
G3  Fine map         → zoom-2 call tree inside the convicted component, EVERY verdict = UNKNOWN
G4  Debugger (zoom 2)→ frame convicted, in & out both cited to trace lines
G5  Hypothesis       → cause proposed (fix proposed, never applied)
```

This ladder is the skill. The sections below are how to execute each rung.

## Two laws that override everything

**Law 1 — the debugger convicts; nothing else may.** A verdict (`sane` / `deviates` / `silent`) is valid only if it is filled from a value captured by `scripts/dap_probe.py` during a repro run through the real flow, cited by its `trace.jsonl` line. These are **banned as sources of any verdict or conviction**, no matter how convincing:

- running the code under investigation in a **standalone process** — `docker exec … python -c`, a REPL, a scratch script, `celery call` outside the probed worker. Executing the real production function in a side process is **not** the flow and **not** the debugger.
- **replicating a transform with standalone tools** to decide what it does — running the transform yourself, outside the flow, to judge a boundary. A replica is a guess dressed in production values; its runtime (library/tool version, flags, environment) may differ from the container's and mislead you.
- static reads, type signatures, tests, prior knowledge, or production breadcrumbs/tags.

Any of these may appear in the report **only after** the DAP conviction, **only** to explain the mechanism behind an already-captured verdict, and **only** clearly labelled as corroboration. If your evidence for *why* rests on a banned source, you have not convicted — say so plainly instead of dressing the shortcut as the method.

**Law 2 — do not *seek* the cause; execute the gate in front of you.** The root cause is an **output** of the bisection, never a target you chase. Every action must be justified by the current gate's exit artifact and nothing else: if the honest reason you are about to run something is "this might show me what's wrong" rather than "this produces the capture this gate requires," that is cause-seeking — and cause-seeking is the exact impulse that manufactures the shortcuts Law 1 bans (replicas, side-channel runs, reasoning ahead of the probe). You do not need a theory of the bug to bisect it: where you look next is fixed by the boundary table — the first hop that deviates, or, when all are `sane`, the narrowest still-suspect segment — not by a hunch. Carry no working theory you are trying to confirm; a probe built to confirm a suspicion has stopped being a bisection. You will know the cause when the frame is convicted at G4, because the process delivered it — not because you went looking.

If you catch yourself already knowing, or hunting for, the answer, that is the signal you left the method. Stop, and return to the capture the current gate demands.

## Inputs — all three required

1. **The error**: a Sentry issue reference or a message + traceback. If it's a Sentry reference and Sentry MCP tools are available, fetch the issue for the authoritative traceback. Production data (breadcrumbs, tags) may only *identify* what to hunt — every claim in the report must cite the local replay's trace.
2. **The artifacts** needed to reproduce the failure.
3. **The reproduction procedure** as the user performed it locally.

If the repro procedure is missing or ambiguous, ask the user before starting. This is the only blocking question allowed; never infer the entry path.

## G0 — Canonical repro

- **Baseline the artifacts in their native form**, using only tools independent of the code under investigation. This is the one sanctioned use of such a tool — on the **raw artifact**, never on anything the code produced. The instant you point that same tool at something the pipeline emitted, you are replicating a transform (Law 1) — stop.
- Formalize the user's procedure into one idempotent script in the scratchpad: reset the state the flow writes (postgres rows, redis keys, minio objects — **local stack only**), inject the artifacts, wait for the outcome, exit non-zero when the failure is observed.
- **Reproduce from the user's actual entry point.** If you replay from a downstream boundary instead of driving the true entry, every hop upstream of your entry stays `UNKNOWN` — you may not call it `sane` without inspecting it — and the report must label the map **partial** and say where the replay joined the flow.
- Run it once **without any debugger** and confirm the exact failure fires. If it doesn't, stop and report — everything downstream depends on this.
- Reuse this script unchanged for every subsequent pass.

**Exit G0:** the repro script fires the exact error. Nothing convicted yet.

## G1 — Coarse map (zoom 1), no debugger

Produce the boundary table and its diagram with **every verdict cell literally `UNKNOWN`**. This empty table is the exit artifact. If you cannot emit it without also stating what's wrong, you are in G4 too early.

1. **Boundary table** (the source of truth, kept in the report): the ordered, *connected* chain of hops from the repro entry point to the raise site — the traceback anchors the tail. Each hop: ID `B1..Bn`, type `call` (function/HTTP), `queue` (Celery/Redis), or `store` (S3/Postgres/Redis-cache), location, **what to capture there**, and `verdict: UNKNOWN`. No gaps: each hop starts where the previous ended.
2. **Render** the table as a Mermaid `sequenceDiagram` with `autonumber` (numbers = boundary IDs).
3. For each **transforming `call` hop** (payload in ≠ payload out) declare, in advance, the **invariant** the transformation must preserve and *what you will capture on both sides* to test it. A plausible container — size, header, schema, count — proves transport, not conservation of content; name the content metric now so you can't later accept transport as proof.
4. Pick the **one quantified oracle metric** the error pattern demands — the measurement that answers, at any hop, "has the failure condition already appeared here?". This same metric is measured at every hop **and** at the G0 baseline; verdicts come from diffing it between consecutive hops. Choose it here, before any values exist.

**Do not execute the code under investigation in this gate** — not through the debugger (that's G2), and never through a banned side channel. G1 is reading and mapping only.

**Exit G1:** boundary table (all `UNKNOWN`) + sequence diagram + declared invariants + declared oracle metric.

## G2 — Debugger, zoom 1

The debugger is the **first** heavy tool you reach after mapping — before any other execution of the flow.

1. **Proof of life first.** Write one probe plan per service (container paths — see debug map). Start `scripts/dap_probe.py` in the background, attach, and confirm every probe reports `verified=True` (root and mirrored `child-*`). If the handshake fails, fix that before anything else — do **not** route around a broken debugger by running the code another way (Law 1).
2. **Fire the repro script** (the G0 one, unchanged) and collect the traces.
3. **Fill each verdict cell only by pasting the `trace.jsonl` line id** that carries the value. A cell you cannot back with a trace line stays `UNKNOWN`. `store` hops are additionally inspected directly between runs (fetch the S3 object / DB row) — a component can return a perfect value yet persist a corrupt one; that inspection is a store read, allowed, and cited as such.
4. **Verdict** per boundary: `sane`, `deviates`, or `silent` (probe never fired — the flow diverged in the segment before it). For a transforming hop, the verdict is the invariant metric measured **in-flow on both sides**, not a replica. Suspect code is never its own oracle.
5. **Validate the map** against the captured stacks: an unmapped actor in a stack (middleware, signal, state-machine hook) becomes a new hop. Record every correction.
6. **Convict a segment**: the first boundary that deviates (or stays silent) convicts segment `Bk → Bk+1`. If every probe is `sane` yet the failure fires, the capture was too shallow: deepen expressions, add a probe that measures the **content** (not the container) at the suspect output, or add `store` hops in the narrowest still-suspect segment — **never** reach for a replica, and never restart the mapping.

**Exit G2:** a convicted segment; every non-`UNKNOWN` verdict cites a trace line.

## G3 — Fine map (zoom 2), no debugger

Build the call tree **inside the convicted segment's component** (IDs `Bk.1, Bk.2, …`): each function on the path, its input and its output, and for each a `verdict: UNKNOWN`. Same rule as G1 — emit the empty tree; do not conclude.

**Subprocess / external-tool boundaries** (the transform runs where you cannot set a Python breakpoint — a shelled-out binary, a C extension, an external service): you still do not get to measure a replica. The plan is to capture, at the **Python frame** around the call, the bytes/handle going **in** and coming **out**, and to measure the oracle metric on the **actual output** in-flow — via a probe expression, or by having the probe/`store` step dump that exact output object for inspection. Only once that in-flow output is convicted may controlled external experiments be used, at G5, to explain *why* the subprocess produced it.

**Exit G3:** zoom-2 call tree with all verdicts `UNKNOWN` and a capture plan for each frame (including the subprocess protocol where relevant).

## G4 — Debugger, zoom 2

Re-run the repro with probes on the inputs and outputs of each function on the path; apply the same discipline as G2 (proof of life, fire, fill from trace ids). Terminate on a **frame conviction**: the method that received sound input and emitted a doomed output, with the trace lines proving **both** sides quoted. For a subprocess boundary, "output" means the captured bytes of the actual subprocess result, measured in-flow — not a rerun of the tool.

**Exit G4:** one convicted frame, input and output both cited to trace lines.

## G5 — Only now, hypotheses

With the frame convicted, formulate what's wrong: the obvious defect if the captured evidence alone explains it (propose the fix, do not apply it), otherwise ranked hypotheses with what evidence would discriminate them. This is where controlled external experiments (including replica runs) legitimately live — to *explain the mechanism* behind the convicted output, clearly labelled as post-conviction corroboration, never as the conviction itself. Never fix anything; the user or another agent takes over.

## Conviction ledger

Keep it in the report. One row per verdict, and a verdict without a trace-line citation is void:

| ID | what was captured | trace line | metric value | verdict |

`UNKNOWN` is a legal, expected value for any hop you did not (or could not) probe — an honest `UNKNOWN` is worth more than a `sane` you cannot cite. The report must show which cells are `UNKNOWN` and why.

## Report

Write `report.md` at the repo root, for a reader who wasn't there:

1. Error summary and origin (Sentry link if any)
2. Repro procedure, verbatim — and, if replayed from a downstream boundary, that fact and where it joined
3. Zoom 1: sequence diagram + boundary table with verdicts, each citing trace lines
4. Zoom 2: call tree + verdicts
5. Conviction — observed facts (each cited) and inferences explicitly labelled as inference
6. Hypotheses / proposed fix (not applied), with any post-conviction corroboration labelled as such
7. Open questions, `UNKNOWN` hops, and map corrections made along the way
8. Paths to raw traces and the repro script (scratchpad)

Also print the conviction summary and the report path in the conversation.

**Never hard-wrap prose.** Write each paragraph as a single line and let it wrap naturally — no fixed line width (not 80, not 100, not 120 chars). Hard-wrapped Markdown breaks when pasted into PRs, issues, and docs. This applies to `report.md` and every file this skill writes.

## Probing with `scripts/dap_probe.py`

```bash
python3 scripts/dap_probe.py plan.json --out trace.jsonl --duration 120
```

Plan schema: see the script's header docstring. Key facts:

- Probe `file` paths are **container paths** (`/app/...`).
- The services run the real work in **child processes** (uvicorn `--reload` server, celery prefork workers). The script mirrors probes into every child session automatically; hits come from `child-*` sessions, and a probe `verified` in `root` but silent there is normal.
- Pauses last milliseconds per hit (capture-and-continue) — safe on live services.
- Use a probe `condition` on noisy boundaries to filter to the failing case.
- To measure **content** at a boundary, prefer a cheap probe `expression` on data already in the frame (a length, a checksum, a slice). Heavy in-frame computation pauses the process longer — if the oracle needs a real tool, have the probe/`store` step dump that exact output object and measure the dump, rather than reaching for a replica of the transform.
- **Never edit source code during a capture run**: watchmedo/uvicorn reload restarts the process and kills every debug session, invalidating the pass.
- If proof-of-life fails, restart the target container for a fresh debugpy listener, re-attach, confirm `verified=True`, **then** fire the repro — never substitute a non-debugger run.

## MCR debug map

| Debug port | Service | Container | Remote root |
|---|---|---|---|
| 5678 | gateway (uvicorn) | mcr-orchestrator | /app/mcr_gateway |
| 7001 | core API (uvicorn) | mcr-core | /app/mcr_meeting |
| 7002 | transcription worker (celery) | mcr-transcription-worker | /app/mcr_meeting |
| 7003 | generation worker (celery) | mcr-generation | /app/mcr_generation |
| 7004 | capture worker (Playwright bot) | mcr-capture-worker | /app/mcr_capture_worker |

- Entry points: frontend/gateway on `:8080`, core API direct on `:8001`. Swagger: `:8001/docs`.
- State inspection/reset: `docker exec mcr-postgres psql -U <user>`, `docker exec mcr-redis redis-cli`, Minio console `:9001` or `mc` in `mcr-minio-setup`.
- Capture worker: probing is safe on replayed scenarios; pausing it during a *live* meeting breaks timing (the meeting moves on without the bot).

## Rules

- Investigation only: never apply a fix, never modify the code under investigation.
- Obey the two laws and the gate order above — they are the point of the skill, not its preamble.
- Every claim cites a trace line or a store inspection; facts and assessments are labelled as such.
- Every quoted measurement names the exact object measured — `⟨metric⟩ of ⟨object at boundary Bk⟩` — never the upstream entity it is assumed to represent. If you measured a boundary's output, attribute the number to that output; do not credit it to the original artifact it is supposed to stand for. If the claim is about the artifact, measure the artifact.
- Local dev stack only; never attach to shared or production environments.

## Execution checklist

Track this as your plan, in order. Do not tick a gate until its **exit** line is true; do not start a gate before the previous one's exit. Before every action, apply the Law-2 test — *is this producing this gate's capture, or am I hunting the cause?*

- [ ] **G0 — Repro**
  - [ ] Confirm the three inputs; ask only if the repro procedure is missing/ambiguous.
  - [ ] Baseline the artifacts in native form with independent tools (raw artifact only).
  - [ ] Write the idempotent repro script (reset local state → inject artifacts → wait → non-zero on failure).
  - [ ] Run it **without any debugger**; confirm the exact error fires. If it replays downstream of the true entry, note where it joins.
  - [ ] **Exit:** the error fires locally; nothing convicted.
- [ ] **G1 — Coarse map (zoom 1), no code execution**
  - [ ] Boundary table `B1..Bn` (id, type, location, what to capture) with every `verdict: UNKNOWN`.
  - [ ] Mermaid `sequenceDiagram` with `autonumber`.
  - [ ] Declare each transforming hop's invariant + both-sides captures; pick the one oracle metric.
  - [ ] **Exit:** empty table + diagram + invariants + oracle metric; no code-under-investigation run.
- [ ] **G2 — Debugger, zoom 1**
  - [ ] Write probe plan(s); start `dap_probe.py`; confirm `verified=True` (root + children). Fix the debugger if it fails — never route around it.
  - [ ] Fire the repro script unchanged; collect traces; inspect `store` hops directly.
  - [ ] Fill each verdict only from a `trace.jsonl` line id; unbacked cells stay `UNKNOWN`.
  - [ ] Validate the map against captured stacks; record corrections.
  - [ ] **Exit:** a segment convicted; every non-`UNKNOWN` verdict cites a trace line.
- [ ] **G3 — Fine map (zoom 2), no code execution**
  - [ ] Call tree `Bk.1..` inside the convicted component (each function's in/out) with all `verdict: UNKNOWN`.
  - [ ] For any subprocess/external boundary, write the in-flow capture plan (bytes in/out at the Python frame; measure the actual output).
  - [ ] **Exit:** empty tree + per-frame capture plan.
- [ ] **G4 — Debugger, zoom 2**
  - [ ] Probe each frame's inputs/outputs; re-run the repro; fill verdicts from trace ids.
  - [ ] **Exit:** one frame convicted, input **and** output both cited to trace lines.
- [ ] **G5 — Hypothesis**
  - [ ] State the defect/ranked hypotheses from captured evidence; add controlled experiments only as labelled post-conviction corroboration.
  - [ ] Propose the fix — never apply it.
- [ ] **Report** — write `report.md` (conviction ledger, `UNKNOWN` hops shown), print the conviction summary + path, no hard-wrapped prose.
