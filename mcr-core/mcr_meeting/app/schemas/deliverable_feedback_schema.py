from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from mcr_meeting.app.models.deliverable_feedback_model import DeliverableFeedbackGroup
from mcr_meeting.app.models.feedback_model import VoteType


class _DeliverableFeedbackUpsertBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comment: str | None = None

    @field_validator("comment", mode="before")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            return None
        return value


class PositiveDeliverableFeedbackUpsertRequest(_DeliverableFeedbackUpsertBase):
    vote_type: Literal[VoteType.POSITIVE]

    @property
    def reasons(self) -> list[str]:
        return []


class NegativeDeliverableFeedbackUpsertRequest(_DeliverableFeedbackUpsertBase):
    vote_type: Literal[VoteType.NEGATIVE]
    reasons: list[str] = Field(default_factory=list)


DeliverableFeedbackUpsertRequest = Annotated[
    PositiveDeliverableFeedbackUpsertRequest | NegativeDeliverableFeedbackUpsertRequest,
    Field(discriminator="vote_type"),
]


class DeliverableFeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vote_type: VoteType
    comment: str | None = None
    reasons: list[str] = Field(default_factory=list)


class ReasonCatalogueEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    deliverable_group: DeliverableFeedbackGroup
    reasons: list[str]
