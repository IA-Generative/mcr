import json

import pytest
from loguru import logger
from pytest import CaptureFixture
from pytest_mock import MockerFixture

import mcr_meeting.app.infrastructure.sentry as sentry_module
from mcr_meeting.app.infrastructure.logger import (
    _json_sink,
    _serialize_record,
    setup_logging,
)


@pytest.fixture
def capture_record():  # type: ignore[no-untyped-def]
    # Isolate from the app's text handler (installed when conftest imports main):
    # its filter mutates the shared record in place, so the capture sink must be
    # the only handler to observe a pristine record. Restore logging on teardown.
    logger.remove()

    def _capture(
        message: str = "hello",
        *,
        request_id: str | None = None,
        level: str = "INFO",
        with_exception: bool = False,
    ):  # type: ignore[no-untyped-def]
        captured = []
        handler_id = logger.add(captured.append, level="DEBUG")
        bound = logger.bind(request_id=request_id) if request_id is not None else logger
        try:
            if with_exception:
                try:
                    raise ValueError("boom")
                except ValueError:
                    bound.opt(exception=True).error(message)
            else:
                bound.log(level, message)
        finally:
            logger.remove(handler_id)
        return captured[0]

    yield _capture

    logger.remove()
    setup_logging()


def test_serialize_record_emits_expected_fields(capture_record) -> None:  # type: ignore[no-untyped-def]
    message = capture_record("hello world", request_id="req-123")

    payload = json.loads(_serialize_record(message.record, "trace-abc", "span-def"))

    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["service"] == "mcr-core"
    assert payload["trace_id"] == "trace-abc"
    assert payload["span_id"] == "span-def"
    assert payload["request_id"] == "req-123"
    assert payload["line"] > 0
    assert "timestamp" in payload


def test_serialize_record_without_trace_or_request_id(capture_record) -> None:  # type: ignore[no-untyped-def]
    message = capture_record("plain")

    payload = json.loads(_serialize_record(message.record, None, None))

    assert payload["trace_id"] is None
    assert payload["span_id"] is None
    assert payload["request_id"] is None


def test_serialize_record_includes_exception_traceback(capture_record) -> None:  # type: ignore[no-untyped-def]
    message = capture_record("it failed", with_exception=True)

    payload = json.loads(_serialize_record(message.record, None, None))

    assert "ValueError" in payload["exception"]
    assert "boom" in payload["exception"]


def test_json_sink_reads_trace_ids_from_owner_and_writes_one_line(
    capture_record, mocker: MockerFixture, capsys: CaptureFixture[str]
) -> None:  # type: ignore[no-untyped-def]
    mocker.patch.object(sentry_module, "current_trace_ids", return_value=("t-1", "s-1"))
    message = capture_record("via sink", request_id="req-9")

    _json_sink(message)

    err = capsys.readouterr().err.strip()
    assert "\n" not in err
    payload = json.loads(err)
    assert payload["message"] == "via sink"
    assert payload["trace_id"] == "t-1"
    assert payload["span_id"] == "s-1"
    assert payload["request_id"] == "req-9"


def test_current_trace_ids_parses_traceparent(mocker: MockerFixture) -> None:
    mocker.patch.object(
        sentry_module.sentry_sdk, "get_traceparent", return_value="abc123-def456-1"
    )

    assert sentry_module.current_trace_ids() == ("abc123", "def456")


def test_current_trace_ids_none_without_active_trace(mocker: MockerFixture) -> None:
    mocker.patch.object(sentry_module.sentry_sdk, "get_traceparent", return_value=None)

    assert sentry_module.current_trace_ids() == (None, None)
