#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""
Stop-hook lint+format runner for the MCR monorepo.

Runs ruff format + ruff check per Python package, and prettier + eslint
for the frontend, on files that are dirty / staged / untracked in git.

Lanes run in parallel; within a lane, format runs before lint to avoid
write races. Output is buffered per-lane and printed in deterministic
order on stderr only when there are blocking issues.

Exit codes:
    0  clean, or only environment issues (missing .venv / node_modules)
    2  blocking: lint violations remain, or format failed (syntax error)

Environment issues (missing tools, no .venv, no node_modules, ruff/eslint
exiting with internal-error codes) print a one-line warning to stderr
and exit 0 — they must not block Claude on a misconfigured machine.

Invoked from .claude/settings.json Stop hook with a 60s budget.
"""

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

PYTHON_PACKAGES = [
    "mcr-core",
    "mcr-gateway",
    "mcr-generation",
    "mcr-capture-worker",
]
FRONTEND_DIR = "mcr-frontend"
FRONTEND_EXTENSIONS = {
    ".vue", ".js", ".jsx", ".cjs", ".mjs", ".ts", ".tsx", ".cts", ".mts",
}

CHUNK_SIZE = 100
TASK_TIMEOUT_S = 45     # hook budget is 60s
MAX_OUTPUT_LINES = 50   # cap each tool's output to protect Claude's context
MAX_WORKERS = 5

# Strip VIRTUAL_ENV / UV_* set by the outer `uv run --script` wrapper so nested
# tool invocations bind to each package's own .venv.
CHILD_ENV = {k: v for k, v in os.environ.items() if not k.startswith("UV_")}
CHILD_ENV.pop("VIRTUAL_ENV", None)


@dataclass
class TaskResult:
    lane: str
    blocking_output: list[str] = field(default_factory=list)
    env_warnings: list[str] = field(default_factory=list)


def repo_root() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=False,
    )
    if out.returncode != 0:
        return Path.cwd()
    return Path(out.stdout.strip())


def collect_changed_files(root: Path) -> list[str]:
    commands = [
        ["git", "-C", str(root), "diff", "-z", "--name-only", "--diff-filter=ACMR"],
        ["git", "-C", str(root), "diff", "-z", "--name-only", "--cached", "--diff-filter=ACMR"],
        ["git", "-C", str(root), "ls-files", "-z", "--others", "--exclude-standard"],
    ]
    paths: set[str] = set()
    for cmd in commands:
        try:
            out = subprocess.run(cmd, capture_output=True, check=False, timeout=10)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []
        if out.returncode != 0:
            continue
        for raw in out.stdout.split(b"\x00"):
            if not raw:
                continue
            try:
                path = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            if (root / path).is_file():
                paths.add(path)
    return sorted(paths)


def bucket_files(files: list[str]) -> dict[str, list[str]]:
    """Group files by lane; out-of-scope files are silently dropped."""
    buckets: dict[str, list[str]] = {}
    for f in files:
        if f.endswith(".py"):
            for pkg in PYTHON_PACKAGES:
                if f.startswith(pkg + "/"):
                    buckets.setdefault(pkg, []).append(f[len(pkg) + 1:])
                    break
            continue
        if f.startswith(FRONTEND_DIR + "/") and Path(f).suffix in FRONTEND_EXTENSIONS:
            buckets.setdefault(FRONTEND_DIR, []).append(f[len(FRONTEND_DIR) + 1:])
    return buckets


def chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def cap_lines(text: str, limit: int) -> str:
    lines = text.splitlines()
    if len(lines) <= limit:
        return text
    return "\n".join(lines[:limit]) + f"\n... {len(lines) - limit} more line(s)"


def run_step(argv: list[str], cwd: Path) -> tuple[int, str]:
    """Run a subprocess and return (exit_code, combined_output). rc=-1 = env error."""
    try:
        out = subprocess.run(
            argv, cwd=str(cwd), capture_output=True, text=True,
            timeout=TASK_TIMEOUT_S, check=False, env=CHILD_ENV,
        )
    except FileNotFoundError as e:
        return -1, f"command not found: {e}"
    except subprocess.TimeoutExpired:
        return -1, f"timed out after {TASK_TIMEOUT_S}s"
    return out.returncode, (out.stdout or "") + (out.stderr or "")


def categorize(
    result: TaskResult, label: str, rc: int, output: str, blocking_codes: set[int],
) -> None:
    """Route subprocess output to blocking_output (code issue) or env_warnings (env issue)."""
    if rc in blocking_codes:
        result.blocking_output.append(f"{label}\n{cap_lines(output, MAX_OUTPUT_LINES)}")
        return
    first_line = (output.strip().splitlines() or [f"exit {rc}"])[0]
    result.env_warnings.append(f"{label}: {first_line}")


def python_lane(pkg: str, files: list[str], root: Path) -> TaskResult:
    result = TaskResult(lane=pkg)
    cwd = root / pkg
    ruff = cwd / ".venv" / "bin" / "ruff"
    if not ruff.exists():
        result.env_warnings.append(f"[{pkg}] .venv missing — run `cd {pkg} && uv sync`")
        return result
    for batch in chunks(files, CHUNK_SIZE):
        rc, output = run_step([str(ruff), "format", *batch], cwd)
        if rc != 0:
            # Parse error in format means check would just re-report it on garbled input.
            categorize(result, f"[{pkg}] ruff format", rc, output, blocking_codes={1, 2})
            continue
        rc, output = run_step([str(ruff), "check", *batch], cwd)
        if rc != 0:
            categorize(result, f"[{pkg}] ruff check", rc, output, blocking_codes={1})
    return result


def frontend_lane(files: list[str], root: Path) -> TaskResult:
    result = TaskResult(lane=FRONTEND_DIR)
    cwd = root / FRONTEND_DIR
    prettier = cwd / "node_modules" / ".bin" / "prettier"
    eslint = cwd / "node_modules" / ".bin" / "eslint"
    if not eslint.exists() or not prettier.exists():
        result.env_warnings.append(
            f"[{FRONTEND_DIR}] node_modules missing — run `cd {FRONTEND_DIR} && pnpm install`"
        )
        return result
    # Prettier scoped to src/ to match the human `pnpm format` workflow.
    prettier_files = [f for f in files if f.startswith("src/")]
    for batch in chunks(prettier_files, CHUNK_SIZE):
        rc, output = run_step([str(prettier), "--write", *batch], cwd)
        if rc != 0:
            categorize(result, f"[{FRONTEND_DIR}] prettier", rc, output, blocking_codes={1, 2})
    for batch in chunks(files, CHUNK_SIZE):
        argv = [str(eslint), "--fix", "--ignore-path", ".gitignore", *batch]
        rc, output = run_step(argv, cwd)
        if rc != 0:
            categorize(result, f"[{FRONTEND_DIR}] eslint", rc, output, blocking_codes={1})
    return result


def main() -> int:
    root = repo_root()
    files = collect_changed_files(root)
    if not files:
        return 0
    buckets = bucket_files(files)
    if not buckets:
        return 0

    results: list[TaskResult] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = []
        for pkg in PYTHON_PACKAGES:
            if pkg in buckets:
                futures.append(pool.submit(python_lane, pkg, buckets[pkg], root))
        if FRONTEND_DIR in buckets:
            futures.append(pool.submit(frontend_lane, buckets[FRONTEND_DIR], root))
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as e:
                # An unexpected lane crash is a hook bug, not Claude's code — never block.
                sys.stderr.write(f"[hook] lane raised {type(e).__name__}: {e}\n")

    results.sort(key=lambda r: r.lane)
    has_blocking = False
    for r in results:
        for warning in r.env_warnings:
            sys.stderr.write(warning + "\n")
        for output in r.blocking_output:
            sys.stderr.write(output + "\n")
            has_blocking = True
    return 2 if has_blocking else 0


if __name__ == "__main__":
    sys.exit(main())
