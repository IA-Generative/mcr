"""no_docstring: enforce docstrings only on public symbols.

A function, method, class, or module is "public" iff it carries a decorator
whose attribute name is in PUBLIC_DECORATOR_ATTRS (HTTP routes, Celery tasks,
CLI commands). Modules are always private (no decorator). Everything else is
private and must not carry a docstring.

Rationale: the project's genuine public surface is announced by a decorator
(`@router.get`, `@celery_app.task`, `@cli.command`, ...). Internal services,
repositories, schemas, and helpers should rely on their names and types.

Escape hatches:

  # lint-ignore: no-docstring
      Suppresses a single docstring violation. For a def/class, place it on the
      `def`/`class` line. For a module docstring, place it on the line just
      above the docstring (or on the same line for a one-line docstring).

  # lint-ignore-file: no-docstring
      Disables the rule for the entire file. Place it anywhere in the file
      (typically near the top).

We avoid `# noqa:` because ruff tries to validate noqa codes and would warn
on a non-ruff code.

Usage:

    # whole package or directory (walked recursively)
    uv run python scripts/lint_rules/no_docstring.py mcr_generation/

    # specific files (e.g. from a pre-commit hook)
    uv run python scripts/lint_rules/no_docstring.py file_a.py file_b.py

Exit code is 0 if clean, 1 if any violation found.
"""

from __future__ import annotations

import ast
import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

PUBLIC_DECORATOR_ATTRS: frozenset[str] = frozenset(
    {
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "task",
        "command",
        "connect",
    }
)

EXCLUDED_DIR_PARTS: frozenset[str] = frozenset(
    {"tests", "migrations", "scripts", "notebooks", ".venv"}
)

RULE_NAME = "no-docstring"
LINE_IGNORE_MARKER = f"lint-ignore: {RULE_NAME}"
FILE_IGNORE_MARKER = f"lint-ignore-file: {RULE_NAME}"

_Definition = ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef


@dataclass(frozen=True)
class Violation:
    path: Path
    lineno: int
    symbol: str
    rule: str = RULE_NAME


# ANSI codes are isolated here so the same Violation can be rendered for the
# CLI (with color) or, later, packaged as an LSP diagnostic (no color, but
# carries the same `rule` field as the diagnostic code).
_ANSI_RESET = "\033[0m"
_ANSI_BOLD = "\033[1m"
_ANSI_RED = "\033[31m"


def _should_use_color(stream: object = sys.stdout) -> bool:
    if "NO_COLOR" in os.environ:
        return False
    isatty = getattr(stream, "isatty", None)
    return bool(isatty and isatty())


def _explainer(symbol: str) -> str:
    return (
        f"docstring on private symbol '{symbol}' "
        f"(add an allowlisted decorator, remove the docstring, "
        f"or use `# {LINE_IGNORE_MARKER}`)"
    )


def format_for_cli(violation: Violation, *, use_color: bool | None = None) -> str:
    if use_color is None:
        use_color = _should_use_color()
    if use_color:
        path = f"{_ANSI_BOLD}{violation.path}:{violation.lineno}{_ANSI_RESET}"
        rule = f"{_ANSI_RED}{violation.rule}{_ANSI_RESET}"
    else:
        path = f"{violation.path}:{violation.lineno}"
        rule = violation.rule
    return f"{path}: {rule}: {_explainer(violation.symbol)}"


def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIR_PARTS for part in path.parts)


def iter_python_files(paths: list[Path]) -> Iterator[Path]:
    for raw in paths:
        if raw.is_file():
            if raw.suffix == ".py" and not is_excluded(raw):
                yield raw
        elif raw.is_dir():
            for found in raw.rglob("*.py"):
                if not is_excluded(found):
                    yield found


def is_public_definition(node: _Definition) -> bool:
    for deco in node.decorator_list:
        target = deco.func if isinstance(deco, ast.Call) else deco
        if isinstance(target, ast.Attribute) and target.attr in PUBLIC_DECORATOR_ATTRS:
            return True
    return False


def find_docstring_line(body: list[ast.stmt]) -> int | None:
    if not body:
        return None
    first = body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return first.lineno
    return None


def has_marker_on_line(source_lines: list[str], lineno: int, marker: str) -> bool:
    index = lineno - 1
    if 0 <= index < len(source_lines):
        return marker in source_lines[index]
    return False


def has_file_ignore(source_lines: list[str]) -> bool:
    return any(FILE_IGNORE_MARKER in line for line in source_lines)


def collect_violations(path: Path) -> list[Violation]:
    source = path.read_text()
    source_lines = source.splitlines()
    if has_file_ignore(source_lines):
        return []

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    violations: list[Violation] = []

    module_doc_line = find_docstring_line(tree.body)
    if module_doc_line is not None and not _is_ignored(
        source_lines, module_doc_line, allow_line_above=True
    ):
        violations.append(Violation(path, module_doc_line, "<module>"))

    for node in ast.walk(tree):
        if not isinstance(node, _Definition):
            continue
        if is_public_definition(node):
            continue
        if _is_ignored(source_lines, node.lineno, allow_line_above=False):
            continue
        doc_line = find_docstring_line(node.body)
        if doc_line is not None:
            violations.append(Violation(path, doc_line, node.name))

    return violations


def _is_ignored(
    source_lines: list[str], lineno: int, *, allow_line_above: bool
) -> bool:
    if has_marker_on_line(source_lines, lineno, LINE_IGNORE_MARKER):
        return True
    if allow_line_above and has_marker_on_line(
        source_lines, lineno - 1, LINE_IGNORE_MARKER
    ):
        return True
    return False


def main(argv: list[str]) -> int:
    raw_paths = [Path(a) for a in argv] or [Path(".")]
    use_color = _should_use_color()
    found = False
    for file_path in iter_python_files(raw_paths):
        for violation in collect_violations(file_path):
            print(format_for_cli(violation, use_color=use_color))
            found = True
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
