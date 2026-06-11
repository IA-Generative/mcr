from pydantic import BaseModel, ConfigDict, Field, field_validator

from mcr_meeting.app.models.feedback_model import (
    FEEDBACK_COMMENT_MAX_LENGTH,
    VoteType,
)


class FeedbackRequest(BaseModel):
    """Base schema for a feedback, containing common attributes."""

    vote_type: VoteType
    comment: str | None = Field(default=None, max_length=FEEDBACK_COMMENT_MAX_LENGTH)
    url: str

    @field_validator("comment", mode="before")
    @classmethod
    def normalize_comment(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            return None
        return v


class Feedback(BaseModel):
    vote_type: VoteType
    comment: str | None = None
    meeting_id: int | None = None


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vote_type: VoteType
    comment: str | None = None
