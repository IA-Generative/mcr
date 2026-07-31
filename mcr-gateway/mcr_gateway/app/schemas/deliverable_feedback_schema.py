from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from mcr_gateway.app.schemas.feedback_schema import VoteType


class _DeliverableFeedbackUpsertBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comment: str | None = None


class PositiveDeliverableFeedbackUpsertRequest(_DeliverableFeedbackUpsertBase):
    vote_type: Literal[VoteType.POSITIVE]


class NegativeDeliverableFeedbackUpsertRequest(_DeliverableFeedbackUpsertBase):
    vote_type: Literal[VoteType.NEGATIVE]
    reasons: list[str] = Field(default_factory=list)


DeliverableFeedbackUpsertRequest = Annotated[
    PositiveDeliverableFeedbackUpsertRequest | NegativeDeliverableFeedbackUpsertRequest,
    Field(discriminator="vote_type"),
]


class DeliverableFeedbackResponse(BaseModel):
    vote_type: VoteType
    comment: str | None = None
    reasons: list[str] = Field(default_factory=list)
