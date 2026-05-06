from fastapi import APIRouter, Depends
from fastapi.responses import Response, StreamingResponse

from mcr_gateway.app.schemas.deliverable_schema import (
    DeliverableCreateRequest,
    DeliverableListResponse,
)
from mcr_gateway.app.schemas.user_schema import Role, TokenUser
from mcr_gateway.app.services.authentification_service import authorize_user
from mcr_gateway.app.services.deliverable_service import (
    get_deliverable_file,
    list_deliverables_for_meeting,
    request_deliverable,
    soft_delete_deliverable,
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


@router.post("/deliverables", tags=["Deliverables"], status_code=202)
async def create_deliverable(
    body: DeliverableCreateRequest,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> Response:
    return await request_deliverable(
        body=body, user_keycloak_uuid=current_user.keycloak_uuid
    )


@router.delete("/deliverables/{deliverable_id}", tags=["Deliverables"], status_code=204)
async def delete_deliverable(
    deliverable_id: int,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> Response:
    return await soft_delete_deliverable(
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
