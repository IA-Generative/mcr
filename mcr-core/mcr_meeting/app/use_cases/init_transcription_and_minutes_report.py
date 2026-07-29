from datetime import datetime, timedelta, timezone

from mcr_meeting.app.db.deliverable_repository import (
    get_active_by_meeting_and_type,
    save_deliverable,
)
from mcr_meeting.app.db.meeting_repository import (
    count_pending_meetings,
    get_meeting_with_owner,
    update_meeting,
)
from mcr_meeting.app.db.meeting_transition_record_repository import (
    save_meeting_transition_record,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.meeting_transitions import (
    init_transcription as apply_init_transcription,
)
from mcr_meeting.app.domain.transcription_queue_estimation import (
    estimate_wait_time_minutes,
)
from mcr_meeting.app.exceptions.exceptions import NotFoundException
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.deliverable_model import (
    Deliverable,
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.meeting_model import MeetingPlatforms
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.use_cases._shared.dispatch_transcription import (
    dispatch_transcription_task,
)


def init_transcription_and_minutes_report(meeting_id: int) -> Meeting:
    meeting = get_meeting_with_owner(meeting_id)
    apply_init_transcription(meeting)

    if meeting.name_platform == MeetingPlatforms.MCR_RECORD:
        meeting.end_date = datetime.now(timezone.utc)

    waiting_time_minutes = estimate_wait_time_minutes(count_pending_meetings())
    now = datetime.now(timezone.utc)
    with UnitOfWork():
        update_meeting(meeting)
        save_deliverable(
            Deliverable(
                meeting_id=meeting.id,
                type=DeliverableType.TRANSCRIPTION,
                status=DeliverableStatus.PENDING,
            )
        )
        _request_default_structured_minutes(meeting.id)
        save_meeting_transition_record(
            MeetingTransitionRecord(
                meeting_id=meeting.id,
                timestamp=now,
                predicted_date_of_next_transition=now
                + timedelta(minutes=waiting_time_minutes),
                status=meeting.status,
            )
        )
        dispatch_transcription_task(meeting.id, str(meeting.owner.keycloak_uuid))

    return meeting


def _request_default_structured_minutes(meeting_id: int) -> None:
    try:
        get_active_by_meeting_and_type(
            meeting_id=meeting_id,
            deliverable_type=DeliverableType.STRUCTURED_MINUTES,
        )
        return
    except NotFoundException:
        pass
    save_deliverable(
        Deliverable(
            meeting_id=meeting_id,
            type=DeliverableType.STRUCTURED_MINUTES,
            status=DeliverableStatus.REQUESTED,
            custom_prompt=None,
        )
    )
