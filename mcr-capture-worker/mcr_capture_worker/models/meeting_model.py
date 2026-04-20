from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mcr_capture_worker.db.db import Base
from mcr_capture_worker.models.user_model import User

if TYPE_CHECKING:
    from playwright.async_api import Page  # noqa: F401

    from mcr_capture_worker.services.connection_strategies.abstract_connection import (
        ConnectionStrategy,
    )
    from mcr_capture_worker.services.meeting_monitors.abstract_meeting_monitor import (
        MeetingMonitor,
    )


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

    def get_connection_strategy(self) -> "ConnectionStrategy":
        raise NotImplementedError

    def get_meeting_monitor(self, page: "Page") -> "MeetingMonitor":
        raise NotImplementedError


class ComuMeeting(Meeting):
    __mapper_args__ = {
        "polymorphic_identity": MeetingPlatform.COMU,
    }

    def get_connection_strategy(self) -> "ConnectionStrategy":
        from mcr_capture_worker.services.connection_strategies import (
            ComuConnectionStrategy,
        )

        return ComuConnectionStrategy()

    def get_meeting_monitor(self, page: "Page") -> "MeetingMonitor":
        from mcr_capture_worker.services.meeting_monitors import ComuMeetingMonitor

        return ComuMeetingMonitor(page)


class WebinaireMeeting(Meeting):
    __mapper_args__ = {
        "polymorphic_identity": MeetingPlatform.WEBINAIRE,
    }

    def get_connection_strategy(self) -> "ConnectionStrategy":
        from mcr_capture_worker.services.connection_strategies import (
            WebinaireConnectionStrategy,
        )

        return WebinaireConnectionStrategy()

    def get_meeting_monitor(self, page: "Page") -> "MeetingMonitor":
        from mcr_capture_worker.services.meeting_monitors import (
            WebinaireMeetingMonitor,
        )

        return WebinaireMeetingMonitor(page)


class WebConfMeeting(Meeting):
    __mapper_args__ = {
        "polymorphic_identity": MeetingPlatform.WEBCONF,
    }

    def get_connection_strategy(self) -> "ConnectionStrategy":
        from mcr_capture_worker.services.connection_strategies import (
            WebConfConnectionStrategy,
        )

        return WebConfConnectionStrategy()

    def get_meeting_monitor(self, page: "Page") -> "MeetingMonitor":
        from mcr_capture_worker.services.meeting_monitors import WebConfMeetingMonitor

        return WebConfMeetingMonitor(page)


class VisiofMeeting(Meeting):
    __mapper_args__ = {
        "polymorphic_identity": MeetingPlatform.VISIO,
    }

    def get_connection_strategy(self) -> "ConnectionStrategy":
        from mcr_capture_worker.services.connection_strategies import (
            VisioStrategy,
        )

        return VisioStrategy()

    def get_meeting_monitor(self, page: "Page") -> "MeetingMonitor":
        from mcr_capture_worker.services.meeting_monitors import VisioMeetingMonitor

        return VisioMeetingMonitor(page)


class WebexMeeting(Meeting):
    __mapper_args__ = {
        "polymorphic_identity": MeetingPlatform.WEBEX,
    }

    def get_connection_strategy(self) -> "ConnectionStrategy":
        from mcr_capture_worker.services.connection_strategies.webex_connection import (
            WebexStrategy,
        )

        return WebexStrategy()

    def get_meeting_monitor(self, page: "Page") -> "MeetingMonitor":
        from mcr_capture_worker.services.meeting_monitors.webex_monitor import (
            WebexMeetingMonitor,
        )

        return WebexMeetingMonitor(page)
