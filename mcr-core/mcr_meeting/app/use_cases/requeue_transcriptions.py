from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum

from loguru import logger

from mcr_meeting.app.db.deliverable_repository import get_active_by_meeting_and_type
from mcr_meeting.app.db.meeting_repository import (
    count_pending_meetings,
    get_meeting_with_owner,
    update_meeting,
)
from mcr_meeting.app.db.meeting_transition_record_repository import (
    save_meeting_transition_record,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.authorize_meeting_access import (
    authorize_meeting_owner_or_admin,
)
from mcr_meeting.app.domain.deliverable_transitions import (
    forced_requeue as forced_requeue_deliverable,
)
from mcr_meeting.app.domain.meeting_transitions import (
    forced_requeue as forced_requeue_meeting,
)
from mcr_meeting.app.domain.transcription_queue_estimation import (
    estimate_wait_time_minutes,
)
from mcr_meeting.app.exceptions.exceptions import (
    DeliverableStateConflictException,
    ForbiddenAccessException,
    MeetingStateConflictException,
    NotFoundException,
)
from mcr_meeting.app.models.deliverable_model import DeliverableType
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.schemas.caller_schema import Caller
from mcr_meeting.app.use_cases._shared.dispatch_transcription import (
    dispatch_transcription_task,
)


class RequeueReason(StrEnum):
    NOT_FOUND = "NOT_FOUND"
    STATE_CONFLICT = "STATE_CONFLICT"
    INTERNAL = "INTERNAL"


@dataclass(frozen=True)
class BatchRequeueResult:
    requeued: list[int]
    failed: list[tuple[int, RequeueReason]]


def requeue_transcriptions(
    meeting_ids: list[int], caller: Caller
) -> BatchRequeueResult:
    requeued: list[int] = []
    failed: list[tuple[int, RequeueReason]] = []
    for meeting_id in meeting_ids:
        try:
            _requeue_one(meeting_id, caller)
            requeued.append(meeting_id)
        except (NotFoundException, ForbiddenAccessException):
            # 403 collapsed into NOT_FOUND so a non-admin owner cannot probe the
            # existence of meetings they do not own.
            failed.append((meeting_id, RequeueReason.NOT_FOUND))
        except (MeetingStateConflictException, DeliverableStateConflictException):
            failed.append((meeting_id, RequeueReason.STATE_CONFLICT))
        except Exception:
            logger.exception("Requeue failed for meeting {}", meeting_id)
            failed.append((meeting_id, RequeueReason.INTERNAL))
    return BatchRequeueResult(requeued=requeued, failed=failed)


def _requeue_one(meeting_id: int, caller: Caller) -> None:
    meeting = get_meeting_with_owner(meeting_id)
    authorize_meeting_owner_or_admin(meeting.user_id, caller)

    deliverable = get_active_by_meeting_and_type(
        meeting_id=meeting.id, deliverable_type=DeliverableType.TRANSCRIPTION
    )

    waiting_minutes = estimate_wait_time_minutes(count_pending_meetings())
    now = datetime.now(timezone.utc)
    with UnitOfWork():
        forced_requeue_meeting(meeting)
        forced_requeue_deliverable(deliverable)
        update_meeting(meeting)
        save_meeting_transition_record(
            MeetingTransitionRecord(
                meeting_id=meeting.id,
                timestamp=now,
                predicted_date_of_next_transition=now
                + timedelta(minutes=waiting_minutes),
                status=meeting.status,
            )
        )
        dispatch_transcription_task(meeting.id, str(meeting.owner.keycloak_uuid))
