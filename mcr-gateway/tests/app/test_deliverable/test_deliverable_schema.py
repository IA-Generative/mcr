import pytest
from pydantic import TypeAdapter, ValidationError

from mcr_gateway.app.schemas.deliverable_schema import (
    DeliverableCreateRequest,
    DeliverableType,
    StructuredDeliverableCreateRequest,
)

_adapter = TypeAdapter(DeliverableCreateRequest)


def test_accepts_structured_minutes_type() -> None:
    request = _adapter.validate_python(
        {"meeting_id": 42, "type": "STRUCTURED_MINUTES"}
    )

    assert isinstance(request, StructuredDeliverableCreateRequest)
    assert request.type == DeliverableType.STRUCTURED_MINUTES


def test_rejects_unknown_type() -> None:
    with pytest.raises(ValidationError):
        _adapter.validate_python({"meeting_id": 42, "type": "UNKNOWN"})
