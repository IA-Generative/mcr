from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mcr_meeting.app.db.db import Base
from mcr_meeting.app.models.feedback_model import VoteType
from mcr_meeting.app.models.types import StrEnumType


class DeliverableFeedbackGroup(StrEnum):
    TRANSCRIPTION = "TRANSCRIPTION"
    STRUCTURED = "STRUCTURED"
    CUSTOM = "CUSTOM"


class TranscriptionFeedbackReason(StrEnum):
    WORD_ERRORS = "WORD_ERRORS"
    MISIDENTIFIED_SPEAKERS = "MISIDENTIFIED_SPEAKERS"
    MISSING_PASSAGES = "MISSING_PASSAGES"
    PUNCTUATION_OR_FORMATTING = "PUNCTUATION_OR_FORMATTING"
    UNRECOGNIZED_ACRONYMS = "UNRECOGNIZED_ACRONYMS"


class StructuredFeedbackReason(StrEnum):
    MISSING_INFORMATION = "MISSING_INFORMATION"
    FACTUAL_ERROR = "FACTUAL_ERROR"
    OFF_TOPIC = "OFF_TOPIC"
    TOO_SHORT_OR_INCOMPLETE = "TOO_SHORT_OR_INCOMPLETE"
    TOO_LONG_OR_DETAILED = "TOO_LONG_OR_DETAILED"
    POOR_STRUCTURE = "POOR_STRUCTURE"


class CustomFeedbackReason(StrEnum):
    PROMPT_NOT_FOLLOWED = "PROMPT_NOT_FOLLOWED"
    FORMAT_NOT_SUITABLE = "FORMAT_NOT_SUITABLE"
    MISSING_INFORMATION = "MISSING_INFORMATION"
    FACTUAL_ERROR = "FACTUAL_ERROR"
    TONE_OR_STYLE_NOT_SUITABLE = "TONE_OR_STYLE_NOT_SUITABLE"


class DeliverableFeedback(Base):
    __tablename__ = "deliverable_feedback"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    deliverable_id: Mapped[int] = mapped_column(
        ForeignKey("deliverable.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    vote_type: Mapped[VoteType] = mapped_column(StrEnumType(VoteType), nullable=False)
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
    reason_rows: Mapped[list["DeliverableFeedbackReason"]] = relationship(
        cascade="all, delete-orphan",
    )
    reasons: AssociationProxy[list[str]] = association_proxy(
        "reason_rows",
        "reason",
        creator=lambda reason: DeliverableFeedbackReason(reason=reason),
    )


class DeliverableFeedbackReason(Base):
    __tablename__ = "deliverable_feedback_reason"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    deliverable_feedback_id: Mapped[int] = mapped_column(
        ForeignKey("deliverable_feedback.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String, nullable=False)
