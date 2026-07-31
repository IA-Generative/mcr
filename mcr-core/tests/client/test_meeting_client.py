import asyncio

import httpx
import pytest
from pytest_mock import MockerFixture

import mcr_meeting.app.infrastructure.meeting_api_client as mac
from mcr_meeting.app.exceptions.celery_exceptions import MeetingDeletedException
from mcr_meeting.app.exceptions.exceptions import TransientInfraError
from mcr_meeting.app.infrastructure.meeting_api_client import _raise_for_core_status

MEETING_ID = 42


def _patch_async_post(mocker: MockerFixture, **async_mock_kwargs: object) -> object:
    """Patch httpx.AsyncClient so its context-managed client.post is controllable."""
    async_client = mocker.patch.object(mac.httpx, "AsyncClient")
    instance = async_client.return_value.__aenter__.return_value
    instance.post = mocker.AsyncMock(**async_mock_kwargs)
    return instance.post


def _response(status_code: int) -> httpx.Response:
    return httpx.Response(status_code, request=httpx.Request("POST", "http://test"))


def test_conflict_is_swallowed() -> None:
    # 409 means the transition already happened: handled, no raise.
    _raise_for_core_status(_response(httpx.codes.CONFLICT), MEETING_ID)


@pytest.mark.parametrize(
    "status_code",
    [httpx.codes.OK, httpx.codes.NO_CONTENT],
)
def test_success_does_not_raise(status_code: int) -> None:
    _raise_for_core_status(_response(status_code), MEETING_ID)


def test_not_found_raises_meeting_deleted() -> None:
    with pytest.raises(MeetingDeletedException):
        _raise_for_core_status(_response(httpx.codes.NOT_FOUND), MEETING_ID)


def test_server_error_raises_http_status_error() -> None:
    with pytest.raises(httpx.HTTPStatusError):
        _raise_for_core_status(_response(httpx.codes.INTERNAL_SERVER_ERROR), MEETING_ID)


def test_transitions_wait_for_slow_core_responses(mocker: MockerFixture) -> None:
    async_client = mocker.patch.object(mac.httpx, "AsyncClient")
    instance = async_client.return_value.__aenter__.return_value
    instance.post = mocker.AsyncMock(return_value=_response(httpx.codes.NO_CONTENT))

    asyncio.run(mac.MeetingApiClient("uuid").mark_transcription_as_success(MEETING_ID))

    timeout = async_client.call_args.kwargs["timeout"]
    assert timeout.read == 30.0
    assert timeout.connect == 5.0


def test_transient_blip_on_transition_is_absorbed(mocker: MockerFixture) -> None:
    # A completed transcription must not be lost to a single network blip on the
    # final "success" callback: the client retries and the transition succeeds.
    post = _patch_async_post(
        mocker,
        side_effect=[
            httpx.ReadTimeout("blip"),
            _response(httpx.codes.NO_CONTENT),
        ],
    )

    asyncio.run(mac.MeetingApiClient("uuid").mark_transcription_as_success(MEETING_ID))

    assert post.await_count == 2


def test_persistent_transient_failure_surfaces_as_transient_infra(
    mocker: MockerFixture,
) -> None:
    # A prolonged core outage must surface as TransientInfraError so the Celery
    # task's autoretry_for re-queues it, instead of dying on a raw httpx error.
    _patch_async_post(mocker, side_effect=httpx.ReadTimeout("down"))

    with pytest.raises(TransientInfraError):
        asyncio.run(
            mac.MeetingApiClient("uuid").mark_transcription_as_success(MEETING_ID)
        )


def test_deleted_meeting_is_not_retried(mocker: MockerFixture) -> None:
    # A 404 is a legitimate terminal answer (meeting deleted), not a transient
    # blip: it must surface immediately without being retried.
    post = _patch_async_post(
        mocker, return_value=_response(httpx.codes.NOT_FOUND)
    )

    with pytest.raises(MeetingDeletedException):
        asyncio.run(
            mac.MeetingApiClient("uuid").mark_transcription_as_success(MEETING_ID)
        )

    assert post.await_count == 1
