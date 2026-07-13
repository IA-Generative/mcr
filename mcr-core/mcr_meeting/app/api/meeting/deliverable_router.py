from fastapi import APIRouter, Depends, Header, Response, status
from fastapi.responses import StreamingResponse
from pydantic import UUID4

from mcr_meeting.app.api._shared.response_headers import create_safe_filename_header
from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.app.db.db import router_db_session_context_manager
from mcr_meeting.app.domain.deliverable_filename import build_deliverable_filename
from mcr_meeting.app.domain.mime_types import DOCX_MIME_TYPE
from mcr_meeting.app.schemas.deliverable_schema import (
    CustomDeliverableCreateRequest,
    DeliverableCreateRequest,
    DeliverableListResponse,
    DeliverableResponse,
    DeliverableSuccessRequest,
)
from mcr_meeting.app.use_cases.ensure_offline_token import ensure_offline_token
from mcr_meeting.app.use_cases.get_deliverable_file import get_deliverable_file
from mcr_meeting.app.use_cases.list_deliverables_for_meeting import (
    list_deliverables_for_meeting,
)
from mcr_meeting.app.use_cases.mark_deliverable_failure import mark_deliverable_failure
from mcr_meeting.app.use_cases.mark_deliverable_success import (
    mark_deliverable_success,
)
from mcr_meeting.app.use_cases.request_deliverable import (
    request_deliverable as request_deliverable_use_case,
)
from mcr_meeting.app.use_cases.soft_delete_deliverable import soft_delete_deliverable

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
    x_user_access_token: str | None = Header(default=None),
) -> DeliverableResponse:
    ensure_offline_token(str(x_user_keycloak_uuid), x_user_access_token)
    custom_prompt = (
        body.custom_prompt if isinstance(body, CustomDeliverableCreateRequest) else None
    )
    deliverable = request_deliverable_use_case(
        meeting_id=body.meeting_id,
        user_keycloak_uuid=x_user_keycloak_uuid,
        deliverable_type=body.type,
        custom_prompt=custom_prompt,
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
    filename = build_deliverable_filename(
        deliverable_type=result.deliverable_type, meeting_name=result.meeting_name
    )
    headers = create_safe_filename_header(filename)
    return StreamingResponse(result.buffer, media_type=DOCX_MIME_TYPE, headers=headers)


@deliverables_router.post("/{deliverable_id}/success")
async def deliverable_success_callback(
    deliverable_id: int,
    body: DeliverableSuccessRequest,
) -> DeliverableResponse:
    deliverable = mark_deliverable_success(
        deliverable_id=deliverable_id,
        report_response=body.report_response,
    )
    return DeliverableResponse.model_validate(deliverable)


@deliverables_router.post("/{deliverable_id}/failure")
async def deliverable_failure_callback(
    deliverable_id: int,
) -> DeliverableResponse:
    deliverable = mark_deliverable_failure(deliverable_id=deliverable_id)
    return DeliverableResponse.model_validate(deliverable)
