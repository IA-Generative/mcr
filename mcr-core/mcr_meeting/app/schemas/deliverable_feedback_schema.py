from pydantic import BaseModel, ConfigDict, field_validator

from mcr_meeting.app.models.feedback_model import VoteType


class DeliverableFeedbackUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vote_type: VoteType
    comment: str | None = None

    @field_validator("comment", mode="before")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            return None
        return value


class DeliverableFeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vote_type: VoteType
    comment: str | None = None
