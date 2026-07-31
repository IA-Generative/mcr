from mcr_meeting.app.domain.deliverable_feedback import (
    ReasonCatalogueEntry,
    build_reason_catalogue,
)
from mcr_meeting.app.models.deliverable_model import DeliverableType


def list_deliverable_feedback_reasons() -> dict[DeliverableType, ReasonCatalogueEntry]:
    return build_reason_catalogue()
