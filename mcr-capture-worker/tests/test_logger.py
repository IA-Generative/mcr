import json
from collections.abc import Callable, Iterator

import pytest
from _pytest.capture import CaptureFixture
from loguru import logger
from pytest_mock import MockerFixture

import mcr_capture_worker.setup.sentry as sentry_module
from mcr_capture_worker.setup.logger import (
    _json_sink,
    _serialize_record,
    setup_logging,
)


@pytest.fixture
def capture_record() -> Iterator[Callable[..., object]]:
    logger.remove()

    def _capture(
        message: str = "hello",
        *,
        level: str = "INFO",
        with_exception: bool = False,
    ) -> object:
        captured: list[object] = []
        handler_id = logger.add(captured.append, level="DEBUG")
        try:
            if with_exception:
                try:
                    raise ValueError("boom")
                except ValueError:
                    logger.opt(exception=True).error(message)
            else:
                logger.log(level, message)
        finally:
            logger.remove(handler_id)
        return captured[0]

    yield _capture

    logger.remove()
    setup_logging()


def test_serialize_record_emits_expected_fields(
    capture_record: Callable[..., object],
) -> None:
    message = capture_record("hello world")

    payload = json.loads(_serialize_record(message.record, "trace-abc", "span-def"))  # type: ignore[attr-defined]

    assert payload["message"] == "hello world"
    assert payload["service"] == "mcr-capture-worker"
    assert payload["trace_id"] == "trace-abc"
    assert payload["span_id"] == "span-def"


def test_serialize_record_without_active_trace(
    capture_record: Callable[..., object],
) -> None:
    message = capture_record("plain")

    payload = json.loads(_serialize_record(message.record, None, None))  # type: ignore[attr-defined]

    assert payload["trace_id"] is None
    assert payload["span_id"] is None


def test_serialize_record_includes_exception_traceback(
    capture_record: Callable[..., object],
) -> None:
    message = capture_record("it failed", with_exception=True)

    payload = json.loads(_serialize_record(message.record, None, None))  # type: ignore[attr-defined]

    assert "ValueError" in payload["exception"]
    assert "boom" in payload["exception"]


def test_json_sink_reads_trace_ids_from_owner_and_writes_one_line(
    capture_record: Callable[..., object],
    mocker: MockerFixture,
    capsys: CaptureFixture[str],
) -> None:
    mocker.patch.object(sentry_module, "current_trace_ids", return_value=("t-1", "s-1"))
    message = capture_record("via sink")

    _json_sink(message)  # type: ignore[arg-type]

    err = capsys.readouterr().err.strip()
    assert "\n" not in err
    payload = json.loads(err)
    assert payload["message"] == "via sink"
    assert payload["trace_id"] == "t-1"
    assert payload["span_id"] == "s-1"


def test_current_trace_ids_parses_traceparent(mocker: MockerFixture) -> None:
    mocker.patch.object(
        sentry_module.sentry_sdk, "get_traceparent", return_value="abc123-def456-1"
    )

    assert sentry_module.current_trace_ids() == ("abc123", "def456")


def test_current_trace_ids_none_without_active_trace(mocker: MockerFixture) -> None:
    mocker.patch.object(sentry_module.sentry_sdk, "get_traceparent", return_value=None)

    assert sentry_module.current_trace_ids() == (None, None)
