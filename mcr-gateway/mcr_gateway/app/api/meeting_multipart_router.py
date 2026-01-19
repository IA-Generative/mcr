from venv import logger

from fastapi import APIRouter, Depends, HTTPException, status

from mcr_gateway.app.schemas.S3_types import (
    MultipartAbortRequest,
    MultipartCompleteRequest,
    MultipartInitRequest,
    MultipartInitResponse,
    MultipartSignPartRequest,
    MultipartSignPartResponse,
)
from mcr_gateway.app.schemas.user_schema import Role, TokenUser
from mcr_gateway.app.services.authentification_service import authorize_user
from mcr_gateway.app.services.meeting_multipart_service import (
    abort_multipart_upload_service,
    complete_multipart_upload_service,
    init_multipart_upload_service,
    sign_multipart_part_service,
)

router = APIRouter()


@router.post(
    "/meetings/{meeting_id}/multipart/init",
    tags=["Meetings", "Audio"],
)
async def init_multipart_upload(
    meeting_id: int,
    init_request: MultipartInitRequest,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> MultipartInitResponse:
    try:
        return await init_multipart_upload_service(
            meeting_id=meeting_id,
            init_request=init_request,
            user_keycloak_uuid=current_user.keycloak_uuid,
        )
    except HTTPException as e:
        logger.error("HTTPException occurred: {}", e.detail)
        raise e


@router.post(
    "/meetings/{meeting_id}/multipart/sign",
    tags=["Meetings", "Audio"],
)
async def sign_multipart_part(
    meeting_id: int,
    sign_request: MultipartSignPartRequest,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> MultipartSignPartResponse:
    try:
        return await sign_multipart_part_service(
            meeting_id=meeting_id,
            sign_request=sign_request,
            user_keycloak_uuid=current_user.keycloak_uuid,
        )
    except HTTPException as e:
        logger.error("HTTPException occurred: {}", e.detail)
        raise e


@router.post(
    "/meetings/{meeting_id}/multipart/complete",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Meetings", "Audio"],
)
async def complete_multipart_upload(
    meeting_id: int,
    complete_request: MultipartCompleteRequest,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> None:
    try:
        await complete_multipart_upload_service(
            meeting_id=meeting_id,
            complete_request=complete_request,
            user_keycloak_uuid=current_user.keycloak_uuid,
        )
    except HTTPException as e:
        logger.error("HTTPException occurred: {}", e.detail)
        raise e


@router.post(
    "/meetings/{meeting_id}/multipart/abort",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Meetings", "Audio"],
)
async def abort_multipart_upload(
    meeting_id: int,
    abort_request: MultipartAbortRequest,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> None:
    try:
        await abort_multipart_upload_service(
            meeting_id=meeting_id,
            abort_request=abort_request,
            user_keycloak_uuid=current_user.keycloak_uuid,
        )
    except HTTPException as e:
        logger.error("HTTPException occurred: {}", e.detail)
        raise e
