from fastapi import APIRouter, Depends, Header, Response, status
from fastapi.responses import StreamingResponse
from pydantic import UUID4

from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.app.db.db import router_db_session_context_manager
from mcr_meeting.app.orchestrators.deliverable_orchestrator import (
    get_deliverable_file,
    list_deliverables_for_meeting,
    mark_deliverable_failure,
    mark_deliverable_success,
    request_deliverable,
    soft_delete_deliverable,
)
from mcr_meeting.app.schemas.deliverable_schema import (
    DeliverableCreateRequest,
    DeliverableListResponse,
    DeliverableResponse,
    DeliverableSuccessRequest,
)
from mcr_meeting.app.utils.file_validation import DOCX_MIME_TYPE
from mcr_meeting.app.utils.filename_header import create_safe_filename_header

api_settings = ApiSettings()

meeting_scoped_router = APIRouter(
    prefix=api_settings.MEETING_API_PREFIX,
    dependencies=[Depends(router_db_session_context_manager)],
    tags=["Deliverables"],
)

deliverables_router = APIRouter(
    prefix=api_settings.DELIVERABLE_API_PREFIX,
    dependencies=[Depends(router_db_session_context_manager)],
    tags=["Deliverables"],
)


@meeting_scoped_router.get("/{meeting_id}/deliverables")
async def list_meeting_deliverables(
    meeting_id: int,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> DeliverableListResponse:
    rows = list_deliverables_for_meeting(
        meeting_id=meeting_id, user_keycloak_uuid=x_user_keycloak_uuid
    )
    return DeliverableListResponse(
        deliverables=[DeliverableResponse.model_validate(row) for row in rows]
    )


@deliverables_router.post(
    "/", status_code=status.HTTP_202_ACCEPTED, response_model=DeliverableResponse
)
async def create_deliverable(
    body: DeliverableCreateRequest,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> DeliverableResponse:
    deliverable = request_deliverable(
        meeting_id=body.meeting_id,
        user_keycloak_uuid=x_user_keycloak_uuid,
        type=body.type,
    )
    return DeliverableResponse.model_validate(deliverable)


@deliverables_router.delete("/{deliverable_id}", status_code=204)
async def delete_deliverable(
    deliverable_id: int,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> Response:
    soft_delete_deliverable(
        deliverable_id=deliverable_id, user_keycloak_uuid=x_user_keycloak_uuid
    )
    return Response(status_code=204)


@deliverables_router.get("/{deliverable_id}/file")
async def get_deliverable_file_route(
    deliverable_id: int,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> StreamingResponse:
    result = get_deliverable_file(
        deliverable_id=deliverable_id, user_keycloak_uuid=x_user_keycloak_uuid
    )
    filename = f"compte_rendu_{result.meeting_name}.docx"
    headers = create_safe_filename_header(filename)
    return StreamingResponse(result.buffer, media_type=DOCX_MIME_TYPE, headers=headers)


@deliverables_router.post("/{deliverable_id}/success")
async def deliverable_success_callback(
    deliverable_id: int,
    body: DeliverableSuccessRequest,
) -> DeliverableResponse:
    deliverable = mark_deliverable_success(
        deliverable_id=deliverable_id,
        external_url=body.external_url,
        report_response=body.report_response,
    )
    return DeliverableResponse.model_validate(deliverable)


@deliverables_router.post("/{deliverable_id}/failure")
async def deliverable_failure_callback(
    deliverable_id: int,
) -> DeliverableResponse:
    deliverable = mark_deliverable_failure(deliverable_id=deliverable_id)
    return DeliverableResponse.model_validate(deliverable)
