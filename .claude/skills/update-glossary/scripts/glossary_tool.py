#!/usr/bin/env python3
"""Diff, merge and check the acronym glossary against its source CSV.

The deterministic half of the /update-glossary skill: it finds what the CSV
carries and the glossary does not, inserts re-synthesised entries at their
alphabetical position, and validates the result. Writing the definitions
themselves is the model's job — see SKILL.md.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

# **ACRO** [ou **VARIANT**] - Signification littérale - Définition.
ENTRY_RE = re.compile(
    r"^\*\*(?P<first>[^*]+)\*\*(?P<variants>.*?) - (?P<literal>.+?) - (?P<definition>.+)$"
)
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
TYPOGRAPHIC_APOSTROPHE = "’"

CSV_ACRONYM = "Acronyme"
CSV_LITERAL = "Signification littérale"
CSV_CONTEXT = "Contexte"
CSV_STATUS = "Statut"
PRODUCTION_STATUS = "Production"


class DuplicateAcronymError(ValueError):
    """Raised when a merge would define the same acronym twice."""


def sort_key(acronym: str) -> str:
    """Alphabetical key: accents stripped, uppercased.

    `TéléRC` sorts as `TELERC`, so accents and inner casing never move an
    entry away from the letter a reader would look it up under.
    """
    stripped = unicodedata.normalize("NFD", acronym).encode("ascii", "ignore").decode()
    return stripped.upper()


def entry_lines(glossary: str) -> list[str]:
    return [line for line in glossary.splitlines() if line.strip()]


def entry_acronyms(line: str) -> list[str]:
    """Every acronym a line defines, including `ou`-joined spelling variants."""
    return [match.strip() for match in BOLD_RE.findall(line)]


def glossary_acronyms(glossary: str) -> set[str]:
    return {
        acronym for line in entry_lines(glossary) for acronym in entry_acronyms(line)
    }


def csv_variants(acronym: str) -> list[str]:
    """`AC / ADCE` in the CSV is one row covering two spellings."""
    return [
        part.strip() for part in re.split(r"\s*/\s*", acronym.strip()) if part.strip()
    ]


def parse_csv(text: str) -> list[dict[str, str]]:
    rows = list(csv.DictReader(io.StringIO(text)))
    return [
        {
            "acronym": (row.get(CSV_ACRONYM) or "").strip(),
            "literal": (row.get(CSV_LITERAL) or "").strip(),
            "context": " ".join((row.get(CSV_CONTEXT) or "").split()),
            "status": (row.get(CSV_STATUS) or "").strip(),
        }
        for row in rows
        if (row.get(CSV_ACRONYM) or "").strip()
    ]


def production_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Only the rows the business has validated.

    The CSV is a live working document. A row still being drafted carries a
    status other than `Production` and must never reach the prompt.
    """
    return [row for row in rows if row["status"] == PRODUCTION_STATUS]


def draft_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if row["status"] != PRODUCTION_STATUS]


def find_missing(rows: list[dict[str, str]], glossary: str) -> list[dict[str, str]]:
    """CSV rows no glossary entry covers, in CSV order.

    A row is covered when any of its spelling variants is already bolded
    somewhere in the glossary — homonyms share a single entry, so an acronym
    present with one meaning covers the row carrying the other.
    """
    known = glossary_acronyms(glossary)
    return [
        row
        for row in rows
        if not any(variant in known for variant in csv_variants(row["acronym"]))
    ]


def merge_entries(glossary: str, new_lines: list[str]) -> str:
    """Insert entries at their alphabetical position and rewrite the file body."""
    existing = entry_lines(glossary)
    seen = {sort_key(acronym) for line in existing for acronym in entry_acronyms(line)}

    cleaned: list[str] = []
    for line in new_lines:
        line = line.strip()
        if not line:
            continue
        match = ENTRY_RE.match(line)
        if not match:
            raise ValueError(
                f"entry does not match `**ACRO** - literal - definition.`: {line!r}"
            )
        if not match.group("definition").rstrip().endswith("."):
            raise ValueError(f"definition must end with a period: {line!r}")
        for acronym in entry_acronyms(line):
            key = sort_key(acronym)
            if key in seen:
                raise DuplicateAcronymError(f"{acronym} is already defined")
            seen.add(key)
        cleaned.append(line)

    merged = sorted(
        existing + cleaned, key=lambda line: sort_key(entry_acronyms(line)[0])
    )
    return "\n\n".join(merged) + "\n"


def check(rows: list[dict[str, str]], glossary: str) -> list[str]:
    """Every rule the merged glossary must satisfy. Empty list means clean."""
    problems: list[str] = []

    for row in find_missing(rows, glossary):
        problems.append(f"absent du glossaire : {row['acronym']} — {row['literal']}")

    lines = entry_lines(glossary)
    for line in lines:
        match = ENTRY_RE.match(line)
        if not match:
            problems.append(f"ligne mal formée : {line}")
            continue
        if not match.group("definition").rstrip().endswith("."):
            problems.append(
                f"définition sans point final : {match.group('first').strip()}"
            )

    if TYPOGRAPHIC_APOSTROPHE in glossary:
        count = glossary.count(TYPOGRAPHIC_APOSTROPHE)
        problems.append(
            f'apostrophe typographique interdite : {count} occurrence(s), utiliser "\'"'
        )

    keys = [sort_key(entry_acronyms(line)[0]) for line in lines if entry_acronyms(line)]
    for previous, current in zip(keys, keys[1:]):
        if previous > current:
            problems.append(f"ordre alphabétique rompu : {previous} précède {current}")

    return problems


# --- CLI ---------------------------------------------------------------


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _cmd_missing(args: argparse.Namespace) -> int:
    all_rows = parse_csv(_read(args.csv))
    rows = production_rows(all_rows)
    drafts = draft_rows(all_rows)
    missing = find_missing(rows, _read(args.glossary))
    print(
        f"# {len(missing)} ligne(s) CSV sans entrée dans le glossaire (sur {len(rows)} en {PRODUCTION_STATUS})\n"
    )
    if drafts:
        listed = ", ".join(f"{row['acronym']} ({row['status']})" for row in drafts)
        print(
            f"# {len(drafts)} brouillon(s) ignoré(s), statut != {PRODUCTION_STATUS} : {listed}\n"
        )
    for row in missing:
        print(f"### {row['acronym']}")
        print(f"LITTERAL: {row['literal']}")
        print(f"CONTEXTE: {row['context']}")
        print()
    return 0


def _cmd_merge(args: argparse.Namespace) -> int:
    glossary_path = Path(args.glossary)
    before = entry_lines(glossary_path.read_text(encoding="utf-8"))
    new_lines = entry_lines(_read(args.entries))
    merged = merge_entries("\n\n".join(before), new_lines)
    glossary_path.write_text(merged, encoding="utf-8")
    print(
        f"{len(before)} → {len(entry_lines(merged))} entrées ({len(new_lines)} ajoutée(s))"
    )
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    rows = production_rows(parse_csv(_read(args.csv))) if args.csv else []
    problems = check(rows, _read(args.glossary))
    if not problems:
        print("OK — aucune entrée manquante, format et ordre conformes.")
        return 0
    print(f"{len(problems)} problème(s) :")
    for problem in problems:
        print(f"  - {problem}")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    missing = sub.add_parser(
        "missing", help="lister les lignes CSV absentes du glossaire"
    )
    missing.add_argument("--csv", required=True)
    missing.add_argument("--glossary", required=True)
    missing.set_defaults(func=_cmd_missing)

    merge = sub.add_parser(
        "merge", help="insérer des entrées rédigées à leur position alphabétique"
    )
    merge.add_argument("--glossary", required=True)
    merge.add_argument(
        "--entries", required=True, help="fichier d'entrées, une par ligne"
    )
    merge.set_defaults(func=_cmd_merge)

    checker = sub.add_parser("check", help="valider couverture, format et ordre")
    checker.add_argument("--glossary", required=True)
    checker.add_argument("--csv", default=None)
    checker.set_defaults(func=_cmd_check)

    args = parser.parse_args(argv)
    try:
        result: Any = args.func(args)
    except (DuplicateAcronymError, ValueError, OSError) as error:
        # The glossary is never half-written: merge_entries validates the whole
        # batch before _cmd_merge touches the file.
        print(f"échec : {error}", file=sys.stderr)
        return 1
    return int(result)


if __name__ == "__main__":
    sys.exit(main())
