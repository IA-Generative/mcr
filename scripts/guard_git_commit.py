#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""
PreToolUse guard: block `git commit` invocations that bypass verification.

Reads the Claude Code PreToolUse hook payload on stdin, finds any `git commit`
in the (possibly compound) Bash command, and denies the call if it carries a
hook-skipping flag:

    --no-verify          skips pre-commit + commit-msg git hooks
    -n / -<bundle>n      short form of --no-verify (e.g. -nm, -an)
    --no-gpg-sign        skips commit signing

On a match it emits the PreToolUse deny decision so Claude never runs the
command. Anything else — non-git commands, safe commits, parse errors — exits 0
silently (fail-open): a bug in this guard must never block legitimate work.
"""

import json
import shlex
import sys

# Single-dash bundles are scanned char-by-char for these; long flags matched whole.
UNSAFE_LONG = {"--no-verify", "--no-gpg-sign"}
UNSAFE_SHORT_CHARS = {"n"}  # `git commit -n` == --no-verify
SEPARATORS = {"&&", "||", "|", ";", "&"}


def unsafe_flags_after_commit(tokens: list[str]) -> list[str]:
    """Return unsafe flags attached to any `git commit` segment of the command."""
    found: list[str] = []
    i = 0
    while i < len(tokens) - 1:
        if tokens[i] == "git" and tokens[i + 1] == "commit":
            j = i + 2
            while j < len(tokens) and tokens[j] not in SEPARATORS:
                tok = tokens[j]
                if tok in UNSAFE_LONG:
                    found.append(tok)
                elif tok.startswith("-") and not tok.startswith("--"):
                    for ch in tok[1:]:
                        if ch in UNSAFE_SHORT_CHARS:
                            found.append(f"-{ch}")
                j += 1
            i = j
            continue
        i += 1
    return found


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    command = (payload.get("tool_input") or {}).get("command", "")
    if not command or "commit" not in command:
        return 0

    try:
        tokens = shlex.split(command)
    except ValueError:
        return 0

    flags = unsafe_flags_after_commit(tokens)
    if not flags:
        return 0

    reason = (
        f"Blocked `git commit` with {', '.join(sorted(set(flags)))}: this bypasses "
        "the project's pre-commit/commit-msg hooks (lint, format, type-check). "
        "Commit without the flag and fix what the hooks report."
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
