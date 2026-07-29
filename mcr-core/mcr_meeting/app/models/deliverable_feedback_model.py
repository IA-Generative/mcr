from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from mcr_meeting.app.db.db import Base
from mcr_meeting.app.models.feedback_model import VoteType


class DeliverableFeedback(Base):
    __tablename__ = "deliverable_feedback"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    deliverable_id: Mapped[int] = mapped_column(
        ForeignKey("deliverable.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    vote_type: Mapped[VoteType] = mapped_column(String, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
