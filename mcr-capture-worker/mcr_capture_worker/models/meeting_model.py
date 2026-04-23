from enum import StrEnum

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mcr_capture_worker.db.db import Base
from mcr_capture_worker.models.user_model import User


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
    - CAPTURE_DONE: Capture completed successfully.
    - DELETED: Meeting was deleted.
    """

    NONE = "NONE"
    CAPTURE_PENDING = "CAPTURE_PENDING"
    CAPTURE_BOT_IS_CONNECTING = "CAPTURE_BOT_IS_CONNECTING"
    CAPTURE_BOT_CONNECTION_FAILED = "CAPTURE_BOT_CONNECTION_FAILED"
    CAPTURE_IN_PROGRESS = "CAPTURE_IN_PROGRESS"
    TRANSCRIPTION_PENDING = "TRANSCRIPTION_PENDING"
    TRANSCRIPTION_IN_PROGRESS = "TRANSCRIPTION_IN_PROGRESS"
    TRANSCRIPTION_FAILED = "TRANSCRIPTION_FAILED"
    TRANSCRIPTION_DONE = "TRANSCRIPTION_DONE"
    CAPTURE_FAILED = "CAPTURE_FAILED"
    CAPTURE_DONE = "CAPTURE_DONE"
    DELETED = "DELETED"


class MeetingPlatform(StrEnum):
    COMU = "COMU"
    WEBINAIRE = "WEBINAIRE"
    WEBCONF = "WEBCONF"
    VISIO = "VISIO"
    WEBEX = "WEBEX"


class Meeting(Base):
    """
    A lightweight ORM model representing a meeting in the database from the capture worker.
    """

    __tablename__ = "meeting"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String, index=True)
    url: Mapped[str | None] = mapped_column(String, index=True)
    name_platform: Mapped[MeetingPlatform] = mapped_column(
        SQLEnum(MeetingPlatform), nullable=False
    )
    status: Mapped[MeetingStatus] = mapped_column(
        SQLEnum(MeetingStatus), default=MeetingStatus.NONE, nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    meeting_platform_id: Mapped[str | None] = mapped_column(String)
    meeting_password: Mapped[str | None] = mapped_column(String)
    owner: Mapped["User"] = relationship()

    __mapper_args__ = {
        "polymorphic_abstract": True,
        "polymorphic_on": name_platform,
    }


class ComuMeeting(Meeting):
    __mapper_args__ = {
        "polymorphic_identity": MeetingPlatform.COMU,
    }


class WebinaireMeeting(Meeting):
    __mapper_args__ = {
        "polymorphic_identity": MeetingPlatform.WEBINAIRE,
    }


class WebConfMeeting(Meeting):
    __mapper_args__ = {
        "polymorphic_identity": MeetingPlatform.WEBCONF,
    }


class VisiofMeeting(Meeting):
    __mapper_args__ = {
        "polymorphic_identity": MeetingPlatform.VISIO,
    }


class WebexMeeting(Meeting):
    __mapper_args__ = {
        "polymorphic_identity": MeetingPlatform.WEBEX,
    }
