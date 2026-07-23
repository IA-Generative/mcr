import json
import uuid

import pytest
from pytest_httpx import HTTPXMock

from mcr_gateway.app.configs.config import settings
from mcr_gateway.app.services.meeting_service import requeue_transcriptions_service


@pytest.mark.asyncio
async def test_passes_through_202(httpx_mock: HTTPXMock) -> None:
    body = {"requeued": [1, 2], "failed": []}
    httpx_mock.add_response(
        method="POST",
        url=f"{settings.MEETING_SERVICE_URL}transcription/requeue",
        json=body,
        status_code=202,
    )

    response = await requeue_transcriptions_service(
        meeting_ids=[1, 2], user_keycloak_uuid=uuid.uuid4(), bearer="jwt-token"
    )

    assert response.status_code == 202
    assert json.loads(response.body) == body


@pytest.mark.asyncio
async def test_passes_through_207_without_flattening(httpx_mock: HTTPXMock) -> None:
    body = {
        "requeued": [1],
        "failed": [{"meeting_id": 2, "reason": "STATE_CONFLICT"}],
    }
    httpx_mock.add_response(
        method="POST",
        url=f"{settings.MEETING_SERVICE_URL}transcription/requeue",
        json=body,
        status_code=207,
    )

    response = await requeue_transcriptions_service(
        meeting_ids=[1, 2], user_keycloak_uuid=uuid.uuid4(), bearer="jwt-token"
    )

    assert response.status_code == 207
    assert json.loads(response.body) == body


@pytest.mark.asyncio
async def test_forwards_bearer_to_core(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{settings.MEETING_SERVICE_URL}transcription/requeue",
        json={"requeued": [1], "failed": []},
        status_code=202,
    )

    await requeue_transcriptions_service(
        meeting_ids=[1], user_keycloak_uuid=uuid.uuid4(), bearer="jwt-token"
    )

    request = httpx_mock.get_requests()[0]
    assert request.headers["Authorization"] == "Bearer jwt-token"
    assert json.loads(request.content) == {"meeting_ids": [1]}
