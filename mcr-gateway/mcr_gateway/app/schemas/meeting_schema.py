from datetime import datetime
from enum import Enum

from pydantic import BaseModel, field_serializer
from pydantic_settings import SettingsConfigDict

from mcr_gateway.app.schemas.deliverable_schema import (
    DeliverableStatus,
    DeliverableType,
)


class MeetingStatus(str, Enum):
    NONE = "NONE"
    CAPTURE_PENDING = "CAPTURE_PENDING"
    IMPORT_PENDING = "IMPORT_PENDING"
    CAPTURE_BOT_IS_CONNECTING = "CAPTURE_BOT_IS_CONNECTING"
    CAPTURE_BOT_CONNECTION_FAILED = "CAPTURE_BOT_CONNECTION_FAILED"
    CAPTURE_IN_PROGRESS = "CAPTURE_IN_PROGRESS"
    TRANSCRIPTION_PENDING = "TRANSCRIPTION_PENDING"
    TRANSCRIPTION_IN_PROGRESS = "TRANSCRIPTION_IN_PROGRESS"
    TRANSCRIPTION_DONE = "TRANSCRIPTION_DONE"
    TRANSCRIPTION_FAILED = "TRANSCRIPTION_FAILED"
    REPORT_PENDING = "REPORT_PENDING"
    REPORT_FAILED = "REPORT_FAILED"
    REPORT_DONE = "REPORT_DONE"
    CAPTURE_FAILED = "CAPTURE_FAILED"
    CAPTURE_DONE = "CAPTURE_DONE"


class MeetingBase(BaseModel):
    """
    Base schema for a meeting.

    Attributes:
        name (str): The name of the meeting.
        url (Optional[str]): The URL for the meeting (if applicable).
        name_platform (str): The name of the platform used for the meeting.
        creation_date (datetime): The creation date and time of the meeting.
        start_date (datetime): The start date and time of the meeting.
        end_date (datetime): The end date and time of the meeting.
        meeting_password (Optional[str]): The password for the meeting (if required).
        meeting_platform_id (Optional[str]): The platform-specific identifier for the meeting.
    """

    name: str
    url: str | None = None
    name_platform: str
    creation_date: datetime
    start_date: datetime | None = None
    end_date: datetime | None = None
    meeting_password: str | None = None
    meeting_platform_id: str | None = None
    notes: str | None = None

    model_config = SettingsConfigDict(
        from_attributes=True,
    )

    @field_serializer("creation_date")
    def serialize_creation_date(self, dt: datetime | None) -> str | None:
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:23] + "Z"


class Meeting(MeetingBase):
    """
    Full schema for a meeting.

    Attributes:
        see MeetingBase for details.
        id (int): The unique identifier of the meeting.
        status (MeetingStatus): The status of the meeting (e.g., scheduled, canceled).
    """

    id: int
    status: MeetingStatus


class MeetingCreate(MeetingBase):
    """
    Schema used for a meeting creation.

    The class was kept for backward compatibility with the old code.

    Attributes:
        see MeetingBase for details.
    """

    pass


class MeetingUpdate(MeetingBase):
    """
    Schema for a meeting update.

    It overrides attributes to allow patch endpoint.
    """

    # As we overide the fields, we need # type: ignore[assignment] for Mypy to stay quiet
    name: str | None = None  # type: ignore[assignment]
    name_platform: str | None = None  # type: ignore[assignment]
    creation_date: datetime | None = None  # type: ignore[assignment]


class DeliverableResponse(BaseModel):
    type: DeliverableType
    status: DeliverableStatus
    external_url: str | None = None
    updated_at: datetime | None = None


class MeetingWithDetails(Meeting):
    deliverables: list[DeliverableResponse] = []


class PaginatedMeetingsResponse(BaseModel):
    total_items: int
    total_pages: int
    page: int
    data: list[MeetingWithDetails]
