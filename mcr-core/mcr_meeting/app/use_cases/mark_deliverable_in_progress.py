from mcr_meeting.app.db import deliverable_repository
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain import deliverable_transitions
from mcr_meeting.app.models.deliverable_model import Deliverable


def mark_deliverable_in_progress(deliverable_id: int) -> Deliverable:
    deliverable = deliverable_repository.get_by_id(deliverable_id)
    deliverable_transitions.mark_in_progress(deliverable)

    with UnitOfWork():
        deliverable_repository.save_deliverable(deliverable)

    return deliverable
