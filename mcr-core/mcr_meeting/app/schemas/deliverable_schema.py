from datetime import datetime

from pydantic import BaseModel, ConfigDict

from mcr_meeting.app.models.deliverable_model import (
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.schemas.report_generation import ReportResponse


class DeliverableResponse(BaseModel):
    id: int
    meeting_id: int
    type: DeliverableType
    status: DeliverableStatus
    external_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeliverableListResponse(BaseModel):
    deliverables: list[DeliverableResponse]


class DeliverableCreateRequest(BaseModel):
    meeting_id: int
    type: DeliverableType


class DeliverableSuccessRequest(BaseModel):
    external_url: str | None = None
    report_response: ReportResponse
