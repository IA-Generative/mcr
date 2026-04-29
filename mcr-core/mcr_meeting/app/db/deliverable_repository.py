from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.exceptions.exceptions import NotFoundException
from mcr_meeting.app.models.deliverable_model import (
    Deliverable,
    DeliverableStatus,
)


def save_deliverable(deliverable: Deliverable) -> Deliverable:
    db = get_db_session_ctx()
    db.add(deliverable)
    db.flush()
    return deliverable


def list_by_meeting(meeting_id: int) -> list[Deliverable]:
    db = get_db_session_ctx()
    return list(
        db.query(Deliverable)
        .filter(
            Deliverable.meeting_id == meeting_id,
            Deliverable.status != DeliverableStatus.DELETED,
        )
        .order_by(Deliverable.created_at.asc())
        .all()
    )


def get_by_id(deliverable_id: int) -> Deliverable:
    db = get_db_session_ctx()
    deliverable = (
        db.query(Deliverable)
        .filter(
            Deliverable.id == deliverable_id,
            Deliverable.status != DeliverableStatus.DELETED,
        )
        .one_or_none()
    )
    if deliverable is None:
        raise NotFoundException(f"Deliverable not found: id={deliverable_id}")
    return deliverable


def set_status(deliverable_id: int, status: DeliverableStatus) -> None:
    db = get_db_session_ctx()
    db.query(Deliverable).filter(Deliverable.id == deliverable_id).update(
        {Deliverable.status: status}
    )


def set_external_url(deliverable_id: int, external_url: str) -> None:
    db = get_db_session_ctx()
    db.query(Deliverable).filter(Deliverable.id == deliverable_id).update(
        {Deliverable.external_url: external_url}
    )


def soft_delete_by_id(deliverable_id: int) -> None:
    set_status(deliverable_id=deliverable_id, status=DeliverableStatus.DELETED)
