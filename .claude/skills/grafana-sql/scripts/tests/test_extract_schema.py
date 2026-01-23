"""Tests for the AST-based schema extraction script."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# Import extract_schema from the parent scripts/ directory
_script_path = Path(__file__).resolve().parent.parent / "extract_schema.py"
_spec = importlib.util.spec_from_file_location("extract_schema", _script_path)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["extract_schema"] = _mod
_spec.loader.exec_module(_mod)

from extract_schema import (  # noqa: E402
    Column,
    Enum,
    Table,
    extract_all,
    extract_from_file,
    format_markdown,
)

# Models directory — resolve relative to project root
MODELS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent.parent / "mcr-core" / "mcr_meeting" / "app" / "models"


@pytest.fixture(scope="module")
def schema() -> tuple[list[Table], list[Enum]]:
    if not MODELS_DIR.is_dir():
        pytest.skip(f"Models directory not found: {MODELS_DIR}")
    return extract_all(MODELS_DIR)


@pytest.fixture(scope="module")
def tables(schema: tuple[list[Table], list[Enum]]) -> list[Table]:
    return schema[0]


@pytest.fixture(scope="module")
def enums(schema: tuple[list[Table], list[Enum]]) -> list[Enum]:
    return schema[1]


def _get_table(tables: list[Table], name: str) -> Table:
    for t in tables:
        if t.name == name:
            return t
    pytest.fail(f"Table '{name}' not found. Available: {[t.name for t in tables]}")


def _get_column(table: Table, name: str) -> Column:
    for c in table.columns:
        if c.name == name:
            return c
    pytest.fail(f"Column '{name}' not found in table '{table.name}'. Available: {[c.name for c in table.columns]}")


def _get_enum(enums: list[Enum], name: str) -> Enum:
    for e in enums:
        if e.name == name:
            return e
    pytest.fail(f"Enum '{name}' not found. Available: {[e.name for e in enums]}")


class TestTableExtraction:
    def test_extracts_all_tables(self, tables: list[Table]) -> None:
        table_names = {t.name for t in tables}
        expected = {"meeting", "user", "transcription", "deliverable", "meeting_transition_record"}
        assert expected == table_names

    def test_meeting_column_count(self, tables: list[Table]) -> None:
        meeting = _get_table(tables, "meeting")
        assert len(meeting.columns) == 13


class TestEnumExtraction:
    def test_extracts_all_enums(self, enums: list[Enum]) -> None:
        enum_names = {e.name for e in enums}
        expected = {"MeetingStatus", "MeetingPlatforms", "MeetingEvent", "Role", "DeliverableFileType", "VoteType"}
        assert expected == enum_names

    def test_meeting_status_values_complete(self, enums: list[Enum]) -> None:
        ms = _get_enum(enums, "MeetingStatus")
        assert len(ms.values) == 15
        assert "NONE" in ms.values
        assert "REPORT_DONE" in ms.values
        assert "DELETED" in ms.values

    def test_meeting_platforms_values_complete(self, enums: list[Enum]) -> None:
        mp = _get_enum(enums, "MeetingPlatforms")
        assert len(mp.values) == 7
        assert "MCR_RECORD" in mp.values
        assert "VISIO" in mp.values
        assert "WEBEX" in mp.values


class TestColumnTypes:
    def test_int_primary_key(self, tables: list[Table]) -> None:
        col = _get_column(_get_table(tables, "meeting"), "id")
        assert col.type == "int"
        assert col.primary_key is True
        assert col.nullable is False

    def test_nullable_string(self, tables: list[Table]) -> None:
        col = _get_column(_get_table(tables, "meeting"), "name")
        assert col.type == "str"
        assert col.nullable is True

    def test_non_nullable_string(self, tables: list[Table]) -> None:
        col = _get_column(_get_table(tables, "user"), "first_name")
        assert col.type == "str"
        assert col.nullable is False

    def test_nullable_datetime(self, tables: list[Table]) -> None:
        col = _get_column(_get_table(tables, "meeting"), "start_date")
        assert col.type == "datetime"
        assert col.nullable is True

    def test_enum_typed_column(self, tables: list[Table]) -> None:
        col = _get_column(_get_table(tables, "meeting"), "status")
        assert col.type == "MeetingStatus"
        assert col.nullable is False

    def test_uuid_type(self, tables: list[Table]) -> None:
        col = _get_column(_get_table(tables, "user"), "keycloak_uuid")
        assert col.type == "UUID"
        assert col.nullable is False


class TestIndexDetection:
    def test_indexed_column(self, tables: list[Table]) -> None:
        col = _get_column(_get_table(tables, "meeting"), "creation_date")
        assert col.indexed is True

    def test_non_indexed_column(self, tables: list[Table]) -> None:
        col = _get_column(_get_table(tables, "meeting"), "status")
        assert col.indexed is False

    def test_unique_column(self, tables: list[Table]) -> None:
        col = _get_column(_get_table(tables, "user"), "email")
        assert col.unique is True

    def test_primary_key_is_indexed(self, tables: list[Table]) -> None:
        col = _get_column(_get_table(tables, "user"), "id")
        assert col.primary_key is True


class TestForeignKeyDetection:
    def test_meeting_user_fk(self, tables: list[Table]) -> None:
        col = _get_column(_get_table(tables, "meeting"), "user_id")
        assert col.fk == "user.id"

    def test_transcription_meeting_fk(self, tables: list[Table]) -> None:
        col = _get_column(_get_table(tables, "transcription"), "meeting_id")
        assert col.fk == "meeting.id"

    def test_deliverable_meeting_fk(self, tables: list[Table]) -> None:
        col = _get_column(_get_table(tables, "deliverable"), "meeting_id")
        assert col.fk == "meeting.id"

    def test_mtr_meeting_fk(self, tables: list[Table]) -> None:
        col = _get_column(_get_table(tables, "meeting_transition_record"), "meeting_id")
        assert col.fk == "meeting.id"


class TestSkipsRelationships:
    def test_no_owner_column(self, tables: list[Table]) -> None:
        meeting = _get_table(tables, "meeting")
        assert "owner" not in {c.name for c in meeting.columns}

    def test_no_transcriptions_column(self, tables: list[Table]) -> None:
        meeting = _get_table(tables, "meeting")
        assert "transcriptions" not in {c.name for c in meeting.columns}

    def test_no_deliverables_column(self, tables: list[Table]) -> None:
        meeting = _get_table(tables, "meeting")
        assert "deliverables" not in {c.name for c in meeting.columns}

    def test_no_meetings_column(self, tables: list[Table]) -> None:
        user = _get_table(tables, "user")
        assert "meetings" not in {c.name for c in user.columns}


class TestMarkdownOutput:
    def test_output_contains_all_table_headers(self, tables: list[Table], enums: list[Enum]) -> None:
        output = format_markdown(tables, enums)
        for table in tables:
            assert f"## Table: {table.name}" in output

    def test_output_contains_all_enum_headers(self, tables: list[Table], enums: list[Enum]) -> None:
        output = format_markdown(tables, enums)
        for enum in enums:
            assert f"## Enum: {enum.name}" in output

    def test_output_table_has_pipe_delimiters(self, tables: list[Table], enums: list[Enum]) -> None:
        output = format_markdown(tables, enums)
        assert "| Column | Type | Nullable | Indexed | FK |" in output


class TestErrorHandling:
    def test_missing_directory_exits(self, tmp_path: Path) -> None:
        fake_dir = tmp_path / "nonexistent"
        with pytest.raises(SystemExit):
            extract_all(fake_dir)

    def test_empty_directory_exits(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty_models"
        empty_dir.mkdir()
        with pytest.raises(SystemExit):
            extract_all(empty_dir)

    def test_file_with_no_models(self, tmp_path: Path) -> None:
        model_file = tmp_path / "dummy_model.py"
        model_file.write_text("x = 1\n")
        tables, enums = extract_from_file(model_file)
        assert tables == []
        assert enums == []
