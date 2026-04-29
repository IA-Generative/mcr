from enum import StrEnum

from pydantic import BaseModel


class VoteType(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"


class FeedbackBase(BaseModel):
    vote_type: VoteType
    comment: str | None = None


class FeedbackRequest(BaseModel):
    """Base schema for a feedback, containing common attributes."""

    vote_type: VoteType
    url: str
    comment: str | None = None


class Feedback(FeedbackBase):
    id: int
