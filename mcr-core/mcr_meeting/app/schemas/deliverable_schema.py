from datetime import datetime
from io import BytesIO
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from mcr_meeting.app.models.deliverable_model import (
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.schemas.deliverable_feedback_schema import (
    DeliverableFeedbackResponse,
)
from mcr_meeting.app.schemas.report_generation import ReportResponse


class DeliverableFileResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    buffer: BytesIO
    meeting_name: str
    deliverable_type: DeliverableType


class DeliverableResponse(BaseModel):
    id: int
    meeting_id: int
    type: DeliverableType
    status: DeliverableStatus
    external_url: str | None
    created_at: datetime
    updated_at: datetime
    feedback: DeliverableFeedbackResponse | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("feedback", mode="before")
    @classmethod
    def hide_retracted_feedback(cls, value: object) -> object:
        if value is not None and not getattr(value, "is_active", True):
            return None
        return value


class DeliverableListResponse(BaseModel):
    deliverables: list[DeliverableResponse]


class StructuredDeliverableCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meeting_id: int
    type: Literal[
        DeliverableType.DECISION_RECORD,
        DeliverableType.DETAILED_SYNTHESIS,
        DeliverableType.STRUCTURED_MINUTES,
    ]


class CustomDeliverableCreateRequest(BaseModel):
    meeting_id: int
    type: Literal[DeliverableType.CUSTOM_REPORT]
    custom_prompt: str = Field(min_length=1)


DeliverableCreateRequest = Annotated[
    StructuredDeliverableCreateRequest | CustomDeliverableCreateRequest,
    Field(discriminator="type"),
]


class DeliverableSuccessRequest(BaseModel):
    report_response: ReportResponse
