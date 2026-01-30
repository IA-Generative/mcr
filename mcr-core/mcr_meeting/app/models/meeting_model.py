from typing import TYPE_CHECKING

if TYPE_CHECKING:  # Avoid circular imports but allow proper typing
    from .transcription_model import Transcription
    from .user_model import User

from datetime import datetime
from enum import StrEnum
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.db import Base


class MeetingPlatforms(StrEnum):
    COMU = "COMU"
    WEBINAIRE = "WEBINAIRE"
    WEBCONF = "WEBCONF"
    MCR_IMPORT = "MCR_IMPORT"
    MCR_RECORD = "MCR_RECORD"


class MeetingStatus(StrEnum):
    """
    Enumeration model for meeting statuses when stored in PG.
    - NONE: Meeting is scheduled but not started.
    - CAPTURE_PENDING: Capture has been requested but not started.
    - CAPTURE_BOT_IS_CONNECTING: Bot is connecting to the meeting.
    - CAPTURE_BOT_CONNECTION_FAILED: Bot failed to connect to the meeting.
    - CAPTURE_IN_PROGRESS: Bot is currently capturing the meeting.
    - TRANSCRIPTION_PENDING: Transcription has been requested but not started.
    - TRANSCRIPTION_DONE: Transcription has been completed.
    - CAPTURE_FAILED: Capture encountered an issue and failed.
    - TRANSCRIPTION_FAILED: Transcription encountered an issue and failed.
    - REPORT_PENDING: Report has but requested
    - REPORT_DONE: Report is available
    """

    NONE = "NONE"
    CAPTURE_PENDING = "CAPTURE_PENDING"
    IMPORT_PENDING = "IMPORT_PENDING"
    CAPTURE_BOT_IS_CONNECTING = "CAPTURE_BOT_IS_CONNECTING"
    CAPTURE_BOT_CONNECTION_FAILED = "CAPTURE_BOT_CONNECTION_FAILED"
    CAPTURE_IN_PROGRESS = "CAPTURE_IN_PROGRESS"
    CAPTURE_DONE = "CAPTURE_DONE"
    TRANSCRIPTION_PENDING = "TRANSCRIPTION_PENDING"
    TRANSCRIPTION_IN_PROGRESS = "TRANSCRIPTION_IN_PROGRESS"
    TRANSCRIPTION_DONE = "TRANSCRIPTION_DONE"
    TRANSCRIPTION_FAILED = "TRANSCRIPTION_FAILED"
    REPORT_PENDING = "REPORT_PENDING"
    REPORT_DONE = "REPORT_DONE"
    CAPTURE_FAILED = "CAPTURE_FAILED"


class MeetingEvent(StrEnum):
    INIT_CAPTURE = "INIT_CAPTURE"
    START_CAPTURE = "START_CAPTURE"
    START_CAPTURE_BOT = "START_CAPTURE_BOT"
    COMPLETE_CAPTURE = "COMPLETE_CAPTURE"
    FAIL_CAPTURE_BOT = "FAIL_CAPTURE_BOT"
    FAIL_CAPTURE = "FAIL_CAPTURE"
    FAIL_TRANSCRIPTION = "FAIL_TRANSCRIPTION"
    INIT_TRANSCRIPTION = "INIT_TRANSCRIPTION"
    START_TRANSCRIPTION = "START_TRANSCRIPTION"
    COMPLETE_TRANSCRIPTION = "COMPLETE_TRANSCRIPTION"
    START_REPORT = "START_REPORT"
    COMPLETE_REPORT = "COMPLETE_REPORT"


class Meeting(Base):
    """
    ORM model representing a meeting in the database.

    Attributes:
        __tablename__ (str): The name of the database table for this model.
        id (int): The unique identifier of the meeting, automatically incremented.
        name (str): The name of the meeting.
        url (str): The URL for accessing the meeting, if applicable.
        name_platform (str): The name of the platform hosting the meeting (e.g., "TEAMS", "COMU").
        creation_date (datetime): The creation time of the meeting.
        start_date (datetime): The start time of the meeting.
        end_date (datetime): The end time of the meeting.
        status (MeetingStatus): The current status of the meeting.
        user_id (int): The ID of the user who created or owns the meeting.
        meeting_platform_id (str): The platform-specific meeting identifier, if applicable.
        meeting_password (str): The password required to join the meeting, if applicable.

    Relationships:
        owner: Links to the `User` model, representing the creator of the meeting.
        transcriptions: Links to the `Transcription` model, representing associated transcriptions.

    Notes:
        - The `transcriptions` relationship includes a cascade delete, ensuring associated
          transcriptions are removed when a meeting is deleted.
        - The `status` field defaults to `MeetingStatus.NONE`.
    """

    __tablename__ = "meeting"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    name: Mapped[Optional[str]] = mapped_column(String, index=True)
    url: Mapped[Optional[str]] = mapped_column(String, index=True)
    name_platform: Mapped[MeetingPlatforms] = mapped_column(
        SQLEnum(MeetingPlatforms), nullable=False
    )
    creation_date: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[MeetingStatus] = mapped_column(
        SQLEnum(MeetingStatus), default=MeetingStatus.NONE, nullable=False
    )
    transcription_filename: Mapped[Optional[str]] = mapped_column(String)
    report_filename: Mapped[Optional[str]] = mapped_column(String)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    meeting_platform_id: Mapped[Optional[str]] = mapped_column(String)
    meeting_password: Mapped[Optional[str]] = mapped_column(String)
    owner: Mapped["User"] = relationship(back_populates="meetings")

    transcriptions: Mapped[List["Transcription"]] = relationship(
        back_populates="meeting",
        cascade="all, delete",
        order_by="Transcription.transcription_index.asc()",
    )

    @property
    def duration_minutes(self) -> Optional[int]:
        if self.start_date is None or self.end_date is None:
            return None

        meeting_duration_seconds = (self.end_date - self.start_date).total_seconds()
        return int(meeting_duration_seconds // 60)
