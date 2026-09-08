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
from mcr_gateway.app.utils.upstream_errors import relay_upstream_errors


@relay_upstream_errors("init multipart upload")
async def init_multipart_upload_service(
    meeting_id: int, init_request: MultipartInitRequest, user_keycloak_uuid: UUID4
) -> MultipartInitResponse:
    async with get_meeting_http_client(user_keycloak_uuid) as client:
        response = await client.post(
            f"{meeting_id}/multipart/init", json=init_request.model_dump()
        )
        response.raise_for_status()
        data = response.json()
        return MultipartInitResponse(**data)


@relay_upstream_errors("sign multipart part")
async def sign_multipart_part_service(
    meeting_id: int,
    sign_request: MultipartSignPartRequest,
    user_keycloak_uuid: UUID4,
) -> MultipartSignPartResponse:
    async with get_meeting_http_client(user_keycloak_uuid) as client:
        response = await client.post(
            f"{meeting_id}/multipart/sign", json=sign_request.model_dump()
        )
        response.raise_for_status()
        data = response.json()
        return MultipartSignPartResponse(**data)


@relay_upstream_errors("complete multipart upload")
async def complete_multipart_upload_service(
    meeting_id: int,
    complete_request: MultipartCompleteRequest,
    user_keycloak_uuid: UUID4,
) -> None:
    async with get_meeting_http_client(user_keycloak_uuid) as client:
        response = await client.post(
            f"{meeting_id}/multipart/complete",
            json=complete_request.model_dump(),
        )
        response.raise_for_status()


@relay_upstream_errors("abort multipart upload")
async def abort_multipart_upload_service(
    meeting_id: int,
    abort_request: MultipartAbortRequest,
    user_keycloak_uuid: UUID4,
) -> None:
    async with get_meeting_http_client(user_keycloak_uuid) as client:
        response = await client.post(
            f"{meeting_id}/multipart/abort", json=abort_request.model_dump()
        )
        response.raise_for_status()
