#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""Preflight for `make start`: catch env misconfiguration before compose runs.

docker compose resolves the ${VAR} interpolations of docker-compose.yaml
with "shell environment > --env-file" precedence. Two silent failure
modes follow, both checked here:

- shadowing: a variable exported by the terminal (VSCode
  terminal.integrated.env, direnv, dotfiles, a leftover `export`)
  overrides any .env edit at every `up`. The classic symptom:
  "I changed .env, restarted, nothing changed."
- shell-only: a variable referenced by docker-compose.yaml exists only
  in the shell, not in the env-files. Everything works on this machine
  and breaks on the next one — and no shadowing warning fires since
  there is no file value to shadow.

Always exits 0: overrides can be deliberate (`FOO=x make start`), so
this must warn, not block.
"""

import os
import re
import sys
from pathlib import Path

# Same files, same order as the Makefile's `docker compose --env-file` flags.
ENV_FILES = [".env.local.docker", ".env"]

# ${VAR}, ${VAR:-default}, ${VAR:?msg}... but not the $${VAR} escapes that
# compose passes through for resolution inside the container.
COMPOSE_VAR_REF = re.compile(r"(?<!\$)\$\{([A-Za-z_][A-Za-z0-9_]*)")


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def warn(lines: list[str]) -> None:
    print("\n".join(lines) + "\n", file=sys.stderr)


def check_shadowing(merged: dict[str, str]) -> None:
    shadowed = [
        (key, os.environ[key], file_value)
        for key, file_value in merged.items()
        if key in os.environ and os.environ[key] != file_value
    ]
    if not shadowed:
        return
    warn(
        [
            "\n⚠️  Variables exported in your shell shadow the env-files"
            " (docker compose: shell > --env-file):",
            *(
                f"   {key}: shell={shell_value!r} overrides env-files={file_value!r}"
                for key, shell_value, file_value in shadowed
            ),
            "   If this is not intentional, find who exports it (VSCode"
            " terminal.integrated.env, direnv,",
            "   ~/.zshrc / ~/.zshenv) and open a fresh terminal."
            " See README > Lancement de MCR en local.",
        ]
    )


def check_shell_only(merged: dict[str, str], compose_refs: set[str]) -> None:
    shell_only = sorted(
        key for key in compose_refs if key not in merged and key in os.environ
    )
    if not shell_only:
        return
    warn(
        [
            "\n⚠️  Variables used by docker-compose.yaml are defined only by your"
            " shell, not in the env-files:",
            *(f"   {key}: shell={os.environ[key]!r}" for key in shell_only),
            "   This works on this machine only. If the variable is meant to"
            " stay, add it to .env or .env.local.docker.",
        ]
    )


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    merged: dict[str, str] = {}
    for name in ENV_FILES:
        merged.update(parse_env_file(root / name))
    compose_refs = set(
        COMPOSE_VAR_REF.findall((root / "docker-compose.yaml").read_text())
    )

    check_shadowing(merged)
    check_shell_only(merged, compose_refs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
