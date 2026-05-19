from enum import StrEnum

from statemachine import StateMachine
from statemachine.exceptions import TransitionNotAllowed
from statemachine.states import States

from mcr_meeting.app.exceptions.exceptions import DeliverableStateConflictException
from mcr_meeting.app.models.deliverable_model import Deliverable, DeliverableStatus


class DeliverableEvent(StrEnum):
    MARK_AVAILABLE = "MARK_AVAILABLE"
    MARK_FAILED = "MARK_FAILED"
    SOFT_DELETE = "SOFT_DELETE"


class DeliverableStateMachine(StateMachine):
    _states = States.from_enum(
        DeliverableStatus,
        initial=DeliverableStatus.PENDING,
        final=DeliverableStatus.DELETED,
        use_enum_instance=True,
    )

    MARK_AVAILABLE = _states.PENDING.to(_states.AVAILABLE)
    MARK_FAILED = _states.PENDING.to(_states.FAILED)
    SOFT_DELETE = (
        _states.PENDING.to(_states.DELETED)
        | _states.AVAILABLE.to(_states.DELETED)
        | _states.FAILED.to(_states.DELETED)
    )


def mark_available(deliverable: Deliverable, external_url: str | None) -> Deliverable:
    _send(deliverable, DeliverableEvent.MARK_AVAILABLE)
    deliverable.external_url = external_url
    return deliverable


def mark_failed(deliverable: Deliverable) -> Deliverable:
    _send(deliverable, DeliverableEvent.MARK_FAILED)
    return deliverable


def soft_delete(deliverable: Deliverable) -> Deliverable:
    _send(deliverable, DeliverableEvent.SOFT_DELETE)
    return deliverable


def _send(deliverable: Deliverable, event: DeliverableEvent) -> None:
    sm = DeliverableStateMachine(start_value=deliverable.status)
    try:
        sm.send(event.value)
    except TransitionNotAllowed as e:
        raise DeliverableStateConflictException(
            f"Cannot apply event {event.value!r} on deliverable in state "
            f"{deliverable.status.value!r}"
        ) from e
    deliverable.status = sm.current_state_value
