from enum import StrEnum

from statemachine import StateMachine
from statemachine.exceptions import TransitionNotAllowed
from statemachine.states import States

from mcr_meeting.app.exceptions.exceptions import DeliverableStateConflictException
from mcr_meeting.app.models.deliverable_model import Deliverable, DeliverableStatus


class DeliverableEvent(StrEnum):
    MARK_IN_PROGRESS = "MARK_IN_PROGRESS"
    MARK_AVAILABLE = "MARK_AVAILABLE"
    MARK_FAILED = "MARK_FAILED"
    REQUEUE = "REQUEUE"
    SOFT_DELETE = "SOFT_DELETE"


class DeliverableStateMachine(StateMachine):
    _states = States.from_enum(
        DeliverableStatus,
        initial=DeliverableStatus.PENDING,
        final=DeliverableStatus.DELETED,
        use_enum_instance=True,
    )

    MARK_IN_PROGRESS = _states.PENDING.to(_states.IN_PROGRESS)
    MARK_AVAILABLE = _states.IN_PROGRESS.to(_states.AVAILABLE)
    MARK_FAILED = _states.PENDING.to(_states.FAILED) | _states.IN_PROGRESS.to(
        _states.FAILED
    )
    REQUEUE = _states.FAILED.to(_states.PENDING)
    SOFT_DELETE = (
        _states.PENDING.to(_states.DELETED)
        | _states.IN_PROGRESS.to(_states.DELETED)
        | _states.AVAILABLE.to(_states.DELETED)
        | _states.FAILED.to(_states.DELETED)
    )


def mark_in_progress(deliverable: Deliverable) -> Deliverable:
    _send(deliverable, DeliverableEvent.MARK_IN_PROGRESS)
    return deliverable


def mark_available(deliverable: Deliverable, external_url: str | None) -> Deliverable:
    _send(deliverable, DeliverableEvent.MARK_AVAILABLE)
    deliverable.external_url = external_url
    return deliverable


def mark_failed(deliverable: Deliverable) -> Deliverable:
    _send(deliverable, DeliverableEvent.MARK_FAILED)
    return deliverable


def requeue(deliverable: Deliverable) -> Deliverable:
    _send(deliverable, DeliverableEvent.REQUEUE)
    return deliverable


def soft_delete(deliverable: Deliverable) -> Deliverable:
    _send(deliverable, DeliverableEvent.SOFT_DELETE)
    return deliverable


def _send(deliverable: Deliverable, event: DeliverableEvent) -> None:
    current = DeliverableStatus(deliverable.status)
    sm = DeliverableStateMachine(start_value=current)
    try:
        sm.send(event.value)
    except TransitionNotAllowed as e:
        raise DeliverableStateConflictException(
            f"Cannot apply event {event.value!r} on deliverable in state "
            f"{current.value!r}"
        ) from e
    deliverable.status = sm.current_state_value
