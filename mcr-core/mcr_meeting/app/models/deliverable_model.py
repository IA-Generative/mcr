from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from mcr_meeting.app.db.db import Base


class DeliverableFileType(StrEnum):
    TRANSCRIPTION = "TRANSCRIPTION"
    REPORT = "REPORT"


class VoteType(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"


class Deliverable(Base):
    __tablename__ = "deliverable"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meeting.id", ondelete="CASCADE")
    )
    file_type: Mapped[DeliverableFileType] = mapped_column(String, nullable=False)
    external_url: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    vote_type: Mapped[VoteType | None] = mapped_column(
        String, nullable=True, default=None
    )
    vote_comment: Mapped[str | None] = mapped_column(
        String, nullable=True, default=None
    )
