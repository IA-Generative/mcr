from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_serializer
from pydantic_settings import SettingsConfigDict


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
    url: Optional[str] = None
    name_platform: str
    creation_date: datetime
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    meeting_password: Optional[str] = None
    meeting_platform_id: Optional[str] = None

    model_config = SettingsConfigDict(
        from_attributes=True,
    )

    @field_serializer("creation_date")
    def serialize_datetime(self, dt: datetime) -> str:
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
    Schema for meeting update

    Attributes:
        see MeetingBase for details.
        status (MeetingStatus): The status of the meeting (e.g., scheduled, canceled).
    """

    pass


class MeetingWithPresignedUrl(BaseModel):
    """
    Schema for a meeting with a presigned URL.

    Attributes:
        meeting (Meeting): The meeting details.
        presigned_url (str): The presigned URL for accessing the meeting.
    """

    meeting: Meeting
    presigned_url: str
