from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class DeliverableType(StrEnum):
    TRANSCRIPTION = "TRANSCRIPTION"
    DECISION_RECORD = "DECISION_RECORD"
    DETAILED_SYNTHESIS = "DETAILED_SYNTHESIS"
    CUSTOM_REPORT = "CUSTOM_REPORT"
    STRUCTURED_MINUTES = "STRUCTURED_MINUTES"


class DeliverableStatus(StrEnum):
    REQUESTED = "REQUESTED"
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    AVAILABLE = "AVAILABLE"
    FAILED = "FAILED"
    DELETED = "DELETED"


class DeliverableResponse(BaseModel):
    id: int
    meeting_id: int
    type: DeliverableType
    status: DeliverableStatus
    external_url: str | None = None
    created_at: datetime
    updated_at: datetime


class DeliverableListResponse(BaseModel):
    deliverables: list[DeliverableResponse]


class StructuredDeliverableCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meeting_id: int
    type: Literal[
        DeliverableType.TRANSCRIPTION,
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
