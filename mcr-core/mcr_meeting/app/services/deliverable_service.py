from mcr_meeting.app.db.deliverable_repository import (
    get_by_id,
    list_by_meeting,
    save_deliverable,
    set_external_url,
    set_status,
    soft_delete_by_id,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.models.deliverable_model import (
    Deliverable,
    DeliverableStatus,
    DeliverableType,
)


def create_pending_deliverable(meeting_id: int, type: DeliverableType) -> Deliverable:
    with UnitOfWork():
        return save_deliverable(
            Deliverable(
                meeting_id=meeting_id,
                type=type,
                status=DeliverableStatus.PENDING,
            )
        )


def mark_deliverable_available(
    deliverable_id: int, external_url: str | None
) -> Deliverable:
    deliverable = get_by_id(deliverable_id=deliverable_id)
    with UnitOfWork():
        if external_url is not None:
            set_external_url(deliverable_id=deliverable_id, external_url=external_url)
        set_status(deliverable_id=deliverable_id, status=DeliverableStatus.AVAILABLE)
    return deliverable


def mark_deliverable_failed(deliverable_id: int) -> Deliverable:
    deliverable = get_by_id(deliverable_id=deliverable_id)
    with UnitOfWork():
        set_status(deliverable_id=deliverable_id, status=DeliverableStatus.FAILED)
    return deliverable


def soft_delete_deliverable_row(deliverable_id: int) -> Deliverable:
    deliverable = get_by_id(deliverable_id=deliverable_id)
    with UnitOfWork():
        soft_delete_by_id(deliverable_id=deliverable_id)
    return deliverable


def list_deliverables_for_meeting(meeting_id: int) -> list[Deliverable]:
    return list_by_meeting(meeting_id=meeting_id)


def get_deliverable(deliverable_id: int) -> Deliverable:
    return get_by_id(deliverable_id=deliverable_id)
