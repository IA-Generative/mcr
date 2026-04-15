#!/usr/bin/env python3
"""Extract database schema from SQLAlchemy model files using AST parsing.

Outputs compact Markdown suitable for LLM context (Grafana SQL skill).
Uses only stdlib — no project dependencies required.

Usage:
    python3 extract_schema.py [models_dir]

If models_dir is not provided, searches relative to common project layouts.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Default search paths relative to the project root
DEFAULT_SEARCH_PATHS = [
    "mcr-core/mcr_meeting/app/models",
    "mcr_meeting/app/models",
]


@dataclass
class Column:
    name: str
    type: str
    nullable: bool = False
    indexed: bool = False
    primary_key: bool = False
    unique: bool = False
    fk: str = ""


@dataclass
class Table:
    name: str
    columns: list[Column] = field(default_factory=list)


@dataclass
class Enum:
    name: str
    values: list[str] = field(default_factory=list)


def parse_mapped_type(annotation: ast.expr) -> tuple[str, bool]:
    """Extract (type_name, nullable) from a Mapped[...] annotation."""
    if not isinstance(annotation, ast.Subscript):
        return str(ast.dump(annotation)), False

    inner = annotation.slice

    # Mapped[list["X"]] — relationship, skip
    if isinstance(inner, ast.Subscript):
        return "", False

    # Mapped[X | None] → BinOp(left=X, op=BitOr, right=None)
    if isinstance(inner, ast.BinOp) and isinstance(inner.op, ast.BitOr):
        nullable = _has_none(inner)
        type_name = _extract_non_none_type(inner)
        return type_name, nullable

    # Mapped[X]
    return _name_of(inner), False


def _has_none(node: ast.BinOp) -> bool:
    for child in (node.left, node.right):
        if isinstance(child, ast.Constant) and child.value is None:
            return True
        if isinstance(child, ast.Name) and child.id == "None":
            return True
    return False


def _extract_non_none_type(node: ast.BinOp) -> str:
    for child in (node.left, node.right):
        if isinstance(child, ast.Constant) and child.value is None:
            continue
        if isinstance(child, ast.Name) and child.id == "None":
            continue
        return _name_of(child)
    return "unknown"


def _name_of(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.Subscript):
        return ""
    return "unknown"


def _get_keyword_bool(call: ast.Call, name: str) -> bool | None:
    for kw in call.keywords:
        if kw.arg == name and isinstance(kw.value, ast.Constant):
            return bool(kw.value.value)
    return None


def _get_fk_target(call: ast.Call) -> str:
    for arg in call.args:
        if isinstance(arg, ast.Call) and _name_of(arg.func) == "ForeignKey":
            if arg.args and isinstance(arg.args[0], ast.Constant):
                return str(arg.args[0].value)
    return ""


def _is_mapped_column(call: ast.Call) -> bool:
    return _name_of(call.func) == "mapped_column"


def _is_relationship(call: ast.Call) -> bool:
    return _name_of(call.func) == "relationship"


def extract_from_file(filepath: Path) -> tuple[list[Table], list[Enum]]:
    """Parse a single model file and return tables and enums."""
    source = filepath.read_text()
    tree = ast.parse(source, filename=str(filepath))

    tables: list[Table] = []
    enums: list[Enum] = []

    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        base_names = [_name_of(b) for b in node.bases]

        if "StrEnum" in base_names:
            enum = Enum(name=node.name)
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            enum.values.append(target.id)
            enums.append(enum)
            continue

        if "Base" not in base_names:
            continue

        tablename = ""
        columns: list[Column] = []

        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "__tablename__":
                        if isinstance(item.value, ast.Constant):
                            tablename = str(item.value.value)

            if not isinstance(item, ast.AnnAssign):
                continue
            if not isinstance(item.target, ast.Name):
                continue

            col_name = item.target.id
            type_name, nullable = parse_mapped_type(item.annotation)

            if not type_name:
                continue
            if item.value and isinstance(item.value, ast.Call) and _is_relationship(item.value):
                continue

            col = Column(name=col_name, type=type_name, nullable=nullable)

            if item.value and isinstance(item.value, ast.Call) and _is_mapped_column(item.value):
                call = item.value
                pk = _get_keyword_bool(call, "primary_key")
                if pk:
                    col.primary_key = True
                idx = _get_keyword_bool(call, "index")
                if idx:
                    col.indexed = True
                uniq = _get_keyword_bool(call, "unique")
                if uniq:
                    col.unique = True
                nul = _get_keyword_bool(call, "nullable")
                if nul is True:
                    col.nullable = True
                if nul is False and col.nullable:
                    col.nullable = False
                col.fk = _get_fk_target(call)

            columns.append(col)

        if tablename:
            tables.append(Table(name=tablename, columns=columns))

    return tables, enums


def extract_all(models_dir: Path) -> tuple[list[Table], list[Enum]]:
    """Extract schema from all model files in the directory."""
    if not models_dir.is_dir():
        print(f"Error: models directory not found: {models_dir}", file=sys.stderr)
        sys.exit(1)

    all_tables: list[Table] = []
    all_enums: list[Enum] = []

    model_files = sorted(models_dir.glob("*_model.py"))
    mtr_file = models_dir / "meeting_transition_record.py"
    if mtr_file.exists():
        model_files.append(mtr_file)

    if not model_files:
        print(f"Error: no model files found in {models_dir}", file=sys.stderr)
        sys.exit(1)

    for filepath in sorted(models_dir.glob("*_model.py")):
        tables, enums = extract_from_file(filepath)
        all_tables.extend(tables)
        all_enums.extend(enums)

    if mtr_file.exists():
        tables, enums = extract_from_file(mtr_file)
        all_tables.extend(tables)
        all_enums.extend(enums)

    return all_tables, all_enums


def format_markdown(tables: list[Table], enums: list[Enum]) -> str:
    """Format extracted schema as compact Markdown."""
    lines: list[str] = []
    lines.append("# Database Schema (auto-extracted from SQLAlchemy models)")
    lines.append("")

    for table in tables:
        lines.append(f"## Table: {table.name}")
        lines.append("| Column | Type | Nullable | Indexed | FK |")
        lines.append("|--------|------|----------|---------|-----|")
        for col in table.columns:
            idx = "PK" if col.primary_key else ("unique" if col.unique else ("yes" if col.indexed else ""))
            lines.append(f"| {col.name} | {col.type} | {'yes' if col.nullable else 'no'} | {idx} | {col.fk} |")
        lines.append("")

    for enum in enums:
        lines.append(f"## Enum: {enum.name}")
        lines.append(", ".join(enum.values))
        lines.append("")

    return "\n".join(lines)


def find_models_dir() -> Path | None:
    """Search for the models directory from the current working directory."""
    cwd = Path.cwd()
    for search_path in DEFAULT_SEARCH_PATHS:
        candidate = cwd / search_path
        if candidate.is_dir():
            return candidate
    return None


def main() -> None:
    if len(sys.argv) > 1:
        models_dir = Path(sys.argv[1])
    else:
        models_dir = find_models_dir()
        if models_dir is None:
            print("Error: could not find models directory. Pass it as an argument.", file=sys.stderr)
            sys.exit(1)

    tables, enums = extract_all(models_dir)
    print(format_markdown(tables, enums))


if __name__ == "__main__":
    main()
