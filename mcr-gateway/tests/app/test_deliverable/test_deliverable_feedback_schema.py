import pytest
from pydantic import TypeAdapter, ValidationError

from mcr_gateway.app.schemas.deliverable_feedback_schema import (
    DeliverableFeedbackUpsertRequest,
    NegativeDeliverableFeedbackUpsertRequest,
    PositiveDeliverableFeedbackUpsertRequest,
)

_adapter = TypeAdapter(DeliverableFeedbackUpsertRequest)


def test_a_thumb_down_carries_the_reasons_it_was_given_for() -> None:
    request = _adapter.validate_python(
        {"vote_type": "NEGATIVE", "reasons": ["OFF_TOPIC", "OTHER"], "comment": "eh"}
    )

    assert isinstance(request, NegativeDeliverableFeedbackUpsertRequest)
    assert request.reasons == ["OFF_TOPIC", "OTHER"]


def test_a_thumb_down_may_carry_no_reason_at_all() -> None:
    request = _adapter.validate_python(
        {"vote_type": "NEGATIVE", "comment": "hard to say, just off"}
    )

    assert isinstance(request, NegativeDeliverableFeedbackUpsertRequest)
    assert request.reasons == []


def test_a_thumb_up_has_no_reasons_to_carry() -> None:
    request = _adapter.validate_python({"vote_type": "POSITIVE", "comment": "great"})

    assert isinstance(request, PositiveDeliverableFeedbackUpsertRequest)


def test_a_thumb_up_carrying_reasons_is_refused_rather_than_trimmed() -> None:
    with pytest.raises(ValidationError):
        _adapter.validate_python(
            {"vote_type": "POSITIVE", "reasons": ["MISSING_INFORMATION"]}
        )


def test_an_unknown_vote_is_refused() -> None:
    with pytest.raises(ValidationError):
        _adapter.validate_python({"vote_type": "SHRUG"})
