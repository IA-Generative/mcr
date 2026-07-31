from fastapi import APIRouter, Depends, status
from fastapi.responses import Response, StreamingResponse

from mcr_gateway.app.schemas.deliverable_feedback_schema import (
    DeliverableFeedbackUpsertRequest,
)
from mcr_gateway.app.schemas.deliverable_schema import (
    DeliverableCreateRequest,
    DeliverableListResponse,
)
from mcr_gateway.app.schemas.user_schema import Role, TokenUser
from mcr_gateway.app.services.authentification_service import authorize_user, security
from mcr_gateway.app.services.deliverable_service import (
    deactivate_deliverable_feedback,
    get_deliverable_file,
    list_deliverables_for_meeting,
    request_deliverable,
    soft_delete_deliverable,
    upsert_deliverable_feedback,
)

router = APIRouter()


@router.get(
    "/meetings/{meeting_id}/deliverables",
    tags=["Deliverables"],
    response_model=DeliverableListResponse,
)
async def list_meeting_deliverables(
    meeting_id: int,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> DeliverableListResponse:
    return await list_deliverables_for_meeting(
        meeting_id=meeting_id, user_keycloak_uuid=current_user.keycloak_uuid
    )


@router.post(
    "/deliverables", tags=["Deliverables"], status_code=status.HTTP_202_ACCEPTED
)
async def create_deliverable(
    body: DeliverableCreateRequest,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
    token: str = Depends(security),
) -> Response:
    return await request_deliverable(
        body=body,
        user_keycloak_uuid=current_user.keycloak_uuid,
        access_token=token,
    )


@router.delete(
    "/deliverables/{deliverable_id}",
    tags=["Deliverables"],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_deliverable(
    deliverable_id: int,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> Response:
    return await soft_delete_deliverable(
        deliverable_id=deliverable_id,
        user_keycloak_uuid=current_user.keycloak_uuid,
    )


@router.put("/deliverables/{deliverable_id}/feedback", tags=["Deliverables"])
async def upsert_deliverable_feedback_route(
    deliverable_id: int,
    body: DeliverableFeedbackUpsertRequest,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> Response:
    return await upsert_deliverable_feedback(
        deliverable_id=deliverable_id,
        body=body,
        user_keycloak_uuid=current_user.keycloak_uuid,
    )


@router.delete(
    "/deliverables/{deliverable_id}/feedback",
    tags=["Deliverables"],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_deliverable_feedback_route(
    deliverable_id: int,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> Response:
    return await deactivate_deliverable_feedback(
        deliverable_id=deliverable_id,
        user_keycloak_uuid=current_user.keycloak_uuid,
    )


@router.get("/deliverables/{deliverable_id}/file", tags=["Deliverables"])
async def get_deliverable_file_route(
    deliverable_id: int,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> StreamingResponse:
    return await get_deliverable_file(
        deliverable_id=deliverable_id,
        user_keycloak_uuid=current_user.keycloak_uuid,
    )
