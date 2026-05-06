from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class DeliverableType(StrEnum):
    TRANSCRIPTION = "TRANSCRIPTION"
    DECISION_RECORD = "DECISION_RECORD"
    DETAILED_SYNTHESIS = "DETAILED_SYNTHESIS"


class DeliverableStatus(StrEnum):
    PENDING = "PENDING"
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


class DeliverableCreateRequest(BaseModel):
    meeting_id: int
    type: DeliverableType
