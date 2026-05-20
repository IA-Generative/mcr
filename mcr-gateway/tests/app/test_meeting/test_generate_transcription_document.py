import uuid

import pytest
from pytest_httpx import HTTPXMock

from mcr_gateway.app.configs.config import settings
from mcr_gateway.app.services.meeting_service import (
    generate_meeting_transcription_document,
)


@pytest.mark.asyncio
async def test_forwards_upstream_content_disposition(httpx_mock: HTTPXMock) -> None:
    user_uuid = uuid.uuid4()
    httpx_mock.add_response(
        method="POST",
        url=f"{settings.MEETING_SERVICE_URL}77/transcription",
        content=b"fake docx content",
        status_code=200,
        headers={
            "content-type": (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
            "content-disposition": (
                "attachment; filename*=UTF-8''Transcription_Ma%20r%C3%A9union.docx"
            ),
        },
    )

    response = await generate_meeting_transcription_document(
        meeting_id=77, user_keycloak_uuid=user_uuid
    )

    assert response.media_type == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert response.headers["content-disposition"] == (
        "attachment; filename*=UTF-8''Transcription_Ma%20r%C3%A9union.docx"
    )


@pytest.mark.asyncio
async def test_omits_disposition_when_upstream_did_not_send_one(
    httpx_mock: HTTPXMock,
) -> None:
    user_uuid = uuid.uuid4()
    httpx_mock.add_response(
        method="POST",
        url=f"{settings.MEETING_SERVICE_URL}77/transcription",
        content=b"fake docx content",
        status_code=200,
        headers={
            "content-type": (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
        },
    )

    response = await generate_meeting_transcription_document(
        meeting_id=77, user_keycloak_uuid=user_uuid
    )

    assert "content-disposition" not in response.headers
