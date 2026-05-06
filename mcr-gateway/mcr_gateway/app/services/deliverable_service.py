from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import HTTPException
from fastapi.responses import Response, StreamingResponse
from loguru import logger
from pydantic import UUID4

from mcr_gateway.app.configs.config import settings
from mcr_gateway.app.schemas.deliverable_schema import (
    DeliverableCreateRequest,
    DeliverableListResponse,
)
from mcr_gateway.app.services.meeting_service import (
    MCRCoreCustomAuth,
    get_meeting_http_client,
)


@asynccontextmanager
async def get_deliverable_http_client(
    user_keycloak_uuid: UUID4,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    client = httpx.AsyncClient(
        base_url=settings.DELIVERABLE_SERVICE_URL,
        auth=MCRCoreCustomAuth(user_keycloak_uuid),
    )
    try:
        yield client
    finally:
        await client.aclose()


async def list_deliverables_for_meeting(
    meeting_id: int, user_keycloak_uuid: UUID4
) -> DeliverableListResponse:
    try:
        async with get_meeting_http_client(user_keycloak_uuid) as client:
            response = await client.get(url=f"{meeting_id}/deliverables")
            response.raise_for_status()
            return DeliverableListResponse.model_validate(response.json())
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Unexpected error listing deliverables: {}", str(e))
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


async def request_deliverable(
    body: DeliverableCreateRequest, user_keycloak_uuid: UUID4
) -> Response:
    try:
        async with get_deliverable_http_client(user_keycloak_uuid) as client:
            response = await client.post(url="", json=body.model_dump(mode="json"))
            response.raise_for_status()
            return Response(
                content=response.content,
                status_code=response.status_code,
                media_type="application/json",
            )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Unexpected error creating deliverable: {}", str(e))
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


async def soft_delete_deliverable(
    deliverable_id: int, user_keycloak_uuid: UUID4
) -> Response:
    try:
        async with get_deliverable_http_client(user_keycloak_uuid) as client:
            response = await client.delete(url=f"{deliverable_id}")
            response.raise_for_status()
            return Response(status_code=204)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Unexpected error deleting deliverable: {}", str(e))
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


async def get_deliverable_file(
    deliverable_id: int, user_keycloak_uuid: UUID4
) -> StreamingResponse:
    try:
        async with get_deliverable_http_client(user_keycloak_uuid) as client:
            response = await client.get(url=f"{deliverable_id}/file")
            response.raise_for_status()
            return StreamingResponse(
                response.aiter_bytes(),
                media_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
                headers={
                    "Content-Disposition": (
                        f"attachment; filename=deliverable_{deliverable_id}.docx"
                    )
                },
            )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Unexpected error fetching deliverable file: {}", str(e))
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
