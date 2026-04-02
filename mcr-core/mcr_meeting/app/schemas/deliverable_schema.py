from pydantic import BaseModel

from mcr_meeting.app.models.deliverable_model import (
    DeliverableFileType,
    VoteType,
)


class VoteRequest(BaseModel):
    """
    Schema for submitting a vote for a deliverable.

    Attributes:
        vote_type: The type of vote (e.g., positive, negative)
        vote_comment: An optional comment explaining the vote
    """

    vote_type: VoteType | None
    vote_comment: str | None


class DeliverableBase(BaseModel):
    """Base schema for a deliverable, containing common attributes."""

    meeting_id: int
    file_type: DeliverableFileType
    external_url: str | None = None
    created_at: str
    updated_at: str
    vote_type: VoteType | None = None
    vote_comment: str | None = None


class DeliverableUpdate(DeliverableBase):
    """
    Model for updating deliverable details.
    """

    pass
