from venv import logger

import httpx
from fastapi import HTTPException
from pydantic import UUID4

from mcr_gateway.app.schemas.S3_types import (
    MultipartAbortRequest,
    MultipartCompleteRequest,
    MultipartInitRequest,
    MultipartInitResponse,
    MultipartSignPartRequest,
    MultipartSignPartResponse,
)
from mcr_gateway.app.services.meeting_service import get_meeting_http_client


async def init_multipart_upload_service(
    meeting_id: int, init_request: MultipartInitRequest, user_keycloak_uuid: UUID4
) -> MultipartInitResponse:
    try:
        async with get_meeting_http_client(user_keycloak_uuid) as client:
            response = await client.post(
                f"{meeting_id}/multipart/init", json=init_request.model_dump()
            )
            response.raise_for_status()
            data = response.json()
            return MultipartInitResponse(**data)

    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error occurred: {} - {}", e.response.status_code, e.response.text
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Unexpected error occurred: {}", str(e))
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


async def sign_multipart_part_service(
    meeting_id: int,
    sign_request: MultipartSignPartRequest,
    user_keycloak_uuid: UUID4,
) -> MultipartSignPartResponse:
    try:
        async with get_meeting_http_client(user_keycloak_uuid) as client:
            response = await client.post(
                f"{meeting_id}/multipart/sign", json=sign_request.model_dump()
            )
            response.raise_for_status()
            data = response.json()
            return MultipartSignPartResponse(**data)
    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error occurred: {} - {}", e.response.status_code, e.response.text
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Unexpected error occurred: {}", str(e))
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


async def complete_multipart_upload_service(
    meeting_id: int,
    complete_request: MultipartCompleteRequest,
    user_keycloak_uuid: UUID4,
) -> None:
    try:
        async with get_meeting_http_client(user_keycloak_uuid) as client:
            response = await client.post(
                f"{meeting_id}/multipart/complete",
                json=complete_request.model_dump(),
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error occurred: {} - {}", e.response.status_code, e.response.text
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Unexpected error occurred: {}", str(e))
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


async def abort_multipart_upload_service(
    meeting_id: int,
    abort_request: MultipartAbortRequest,
    user_keycloak_uuid: UUID4,
) -> None:
    try:
        async with get_meeting_http_client(user_keycloak_uuid) as client:
            response = await client.post(
                f"{meeting_id}/multipart/abort", json=abort_request.model_dump()
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error occurred: {} - {}", e.response.status_code, e.response.text
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Unexpected error occurred: {}", str(e))
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
