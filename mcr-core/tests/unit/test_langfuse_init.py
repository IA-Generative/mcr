from typing import Any

from pytest_mock import MockerFixture

from mcr_meeting.app.infrastructure.langfuse import init_langfuse


def _patch_langfuse(mocker: MockerFixture, *, auth_check: bool | Exception) -> Any:
    client = mocker.MagicMock()
    if isinstance(auth_check, Exception):
        client.auth_check.side_effect = auth_check
    else:
        client.auth_check.return_value = auth_check
    mocker.patch(
        "mcr_meeting.app.infrastructure.langfuse.Langfuse", return_value=client
    )
    return client


def test_rejected_credentials_leave_no_exporter_running(
    mocker: MockerFixture,
) -> None:
    """Constructing Langfuse already started a background OTLP exporter.

    Left alive on rejected credentials it keeps POSTing spans on every flush
    interval, each one failing — the worker burns network on work that can
    never land and floods Sentry with the failures.
    """
    client = _patch_langfuse(mocker, auth_check=False)

    init_langfuse()

    client.shutdown.assert_called_once()


def test_rejected_credentials_do_not_prevent_startup(
    mocker: MockerFixture,
) -> None:
    """Invalid credentials raise from auth_check: transcription must still boot."""
    client = _patch_langfuse(mocker, auth_check=Exception("UnauthorizedError"))

    init_langfuse()

    client.shutdown.assert_called_once()


def test_accepted_credentials_keep_the_exporter_running(
    mocker: MockerFixture,
) -> None:
    client = _patch_langfuse(mocker, auth_check=True)

    init_langfuse()

    client.shutdown.assert_not_called()


def test_startup_survives_a_failing_shutdown(mocker: MockerFixture) -> None:
    """Tracing teardown is best-effort: it must never take the worker down."""
    client = _patch_langfuse(mocker, auth_check=False)
    client.shutdown.side_effect = Exception("shutdown failed")

    init_langfuse()

    client.shutdown.assert_called_once()
