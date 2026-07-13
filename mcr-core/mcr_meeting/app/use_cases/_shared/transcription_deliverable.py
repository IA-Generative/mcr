from mcr_meeting.app.db.deliverable_repository import (
    find_active_by_meeting_and_type,
    save_deliverable,
)
from mcr_meeting.app.domain.deliverable_transitions import (
    mark_available,
    mark_failed,
    mark_in_progress,
    requeue,
)
from mcr_meeting.app.models.deliverable_model import (
    Deliverable,
    DeliverableStatus,
    DeliverableType,
)


def queue_transcription_deliverable(meeting_id: int) -> Deliverable:
    existing = _find(meeting_id)
    if existing is None:
        return _create(meeting_id, DeliverableStatus.PENDING)
    return requeue(existing)


def start_transcription_deliverable(meeting_id: int) -> Deliverable:
    existing = _find(meeting_id)
    if existing is None:
        return _create(meeting_id, DeliverableStatus.IN_PROGRESS)
    return mark_in_progress(existing)


def complete_transcription_deliverable(
    meeting_id: int, external_url: str | None
) -> Deliverable:
    existing = _find(meeting_id)
    if existing is None:
        return _create(meeting_id, DeliverableStatus.AVAILABLE, external_url)
    return mark_available(existing, external_url)


def fail_transcription_deliverable(meeting_id: int) -> Deliverable:
    existing = _find(meeting_id)
    if existing is None:
        return _create(meeting_id, DeliverableStatus.FAILED)
    return mark_failed(existing)


def _find(meeting_id: int) -> Deliverable | None:
    return find_active_by_meeting_and_type(
        meeting_id=meeting_id, deliverable_type=DeliverableType.TRANSCRIPTION
    )


def _create(
    meeting_id: int, status: DeliverableStatus, external_url: str | None = None
) -> Deliverable:
    return save_deliverable(
        Deliverable(
            meeting_id=meeting_id,
            type=DeliverableType.TRANSCRIPTION,
            status=status,
            external_url=external_url,
        )
    )
