import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from pytest_httpx import HTTPXMock

from mcr_gateway.app.configs.config import settings
from mcr_gateway.app.schemas.deliverable_schema import DeliverableCreateRequest
from mcr_gateway.app.services.deliverable_service import (
    get_deliverable_file,
    list_deliverables_for_meeting,
    request_deliverable,
    soft_delete_deliverable,
)


def _deliverable_payload(deliverable_id: int = 1, meeting_id: int = 42) -> dict:
    return {
        "id": deliverable_id,
        "meeting_id": meeting_id,
        "type": "DECISION_RECORD",
        "status": "AVAILABLE",
        "external_url": None,
        "created_at": datetime(2026, 4, 28, tzinfo=timezone.utc).isoformat(),
        "updated_at": datetime(2026, 4, 28, tzinfo=timezone.utc).isoformat(),
    }


@pytest.mark.asyncio
async def test_list_deliverables_forwards_request_and_returns_rows(
    httpx_mock: HTTPXMock,
) -> None:
    meeting_id = 42
    user_uuid = uuid.uuid4()
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.MEETING_SERVICE_URL}{meeting_id}/deliverables",
        json={
            "deliverables": [
                _deliverable_payload(deliverable_id=1, meeting_id=meeting_id),
                _deliverable_payload(deliverable_id=2, meeting_id=meeting_id),
            ]
        },
        status_code=200,
    )

    result = await list_deliverables_for_meeting(
        meeting_id=meeting_id, user_keycloak_uuid=user_uuid
    )

    assert len(result.deliverables) == 2
    assert result.deliverables[0].id == 1
    assert result.deliverables[0].type == "DECISION_RECORD"


@pytest.mark.asyncio
async def test_create_deliverable_forwards_body_and_returns_202(
    httpx_mock: HTTPXMock,
) -> None:
    user_uuid = uuid.uuid4()
    httpx_mock.add_response(
        method="POST",
        url=f"{settings.DELIVERABLE_SERVICE_URL}",
        json=_deliverable_payload(deliverable_id=99, meeting_id=42),
        status_code=202,
    )

    body = DeliverableCreateRequest(meeting_id=42, type="DECISION_RECORD")
    response = await request_deliverable(body=body, user_keycloak_uuid=user_uuid)

    assert response.status_code == 202


@pytest.mark.asyncio
async def test_create_deliverable_propagates_400_for_transcription(
    httpx_mock: HTTPXMock,
) -> None:
    user_uuid = uuid.uuid4()
    httpx_mock.add_response(
        method="POST",
        url=f"{settings.DELIVERABLE_SERVICE_URL}",
        json={"detail": "TRANSCRIPTION deliverables cannot be requested"},
        status_code=400,
    )

    body = DeliverableCreateRequest(meeting_id=42, type="TRANSCRIPTION")
    with pytest.raises(HTTPException) as exc:
        await request_deliverable(body=body, user_keycloak_uuid=user_uuid)

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_delete_deliverable_returns_204(httpx_mock: HTTPXMock) -> None:
    user_uuid = uuid.uuid4()
    httpx_mock.add_response(
        method="DELETE",
        url=f"{settings.DELIVERABLE_SERVICE_URL}77",
        status_code=204,
    )

    response = await soft_delete_deliverable(
        deliverable_id=77, user_keycloak_uuid=user_uuid
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_get_file_streams_docx(httpx_mock: HTTPXMock) -> None:
    user_uuid = uuid.uuid4()
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.DELIVERABLE_SERVICE_URL}77/file",
        content=b"fake docx content",
        status_code=200,
        headers={
            "content-type": (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        },
    )

    response = await get_deliverable_file(
        deliverable_id=77, user_keycloak_uuid=user_uuid
    )

    assert response.media_type == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@pytest.mark.asyncio
async def test_non_owner_propagates_403(httpx_mock: HTTPXMock) -> None:
    user_uuid = uuid.uuid4()
    httpx_mock.add_response(
        method="DELETE",
        url=f"{settings.DELIVERABLE_SERVICE_URL}77",
        json={"detail": "Meeting is owned by a different user"},
        status_code=403,
    )

    with pytest.raises(HTTPException) as exc:
        await soft_delete_deliverable(deliverable_id=77, user_keycloak_uuid=user_uuid)

    assert exc.value.status_code == 403
