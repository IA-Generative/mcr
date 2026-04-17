from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db.db import Base


class VoteType(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"


class Feedback(Base):
    """
    User feedback as a vote with an optional free-text comment.

    Captures positive or negative votes submitted by users, along with an optional
    comment. The navigation context (meeting page) can be recorded via `meeting_id`
    to enable contextual statistics.

    Attributes:
        id: Auto-incremented primary key.
        user_id: ID of the user who submitted the feedback (required).
                 Cascade-deleted when the user is deleted.
        vote_type: Vote value — POSITIVE or NEGATIVE. Optional.
        comment: Free-text comment attached to the vote. Optional, max 1000 characters.
        meeting_id: ID of the meeting the user was viewing when they submitted the
                    feedback. Optional — used for contextual statistics.
                    Set to NULL when the meeting is deleted.
        created_at: Feedback creation timestamp (UTC).
    """

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    vote_type: Mapped[VoteType | None] = mapped_column(String)
    comment: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, default=None
    )
    meeting_id: Mapped[int | None] = mapped_column(
        ForeignKey("meeting.id", ondelete="SET NULL"), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
