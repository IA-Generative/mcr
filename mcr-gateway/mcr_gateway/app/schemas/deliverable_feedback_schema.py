from pydantic import BaseModel, ConfigDict

from mcr_gateway.app.schemas.feedback_schema import VoteType


class DeliverableFeedbackUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vote_type: VoteType
    comment: str | None = None


class DeliverableFeedbackResponse(BaseModel):
    vote_type: VoteType
    comment: str | None = None
