import uuid
from unittest.mock import Mock

from pytest_mock import MockerFixture
from sqlalchemy.orm import Session

from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.models.deliverable_model import (
    Deliverable,
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.meeting_model import (
    Meeting,
    MeetingPlatforms,
    MeetingStatus,
)
from mcr_meeting.app.schemas.caller_schema import Caller
from mcr_meeting.app.use_cases import requeue_transcriptions as uc
from mcr_meeting.app.use_cases.requeue_transcriptions import (
    RequeueReason,
    requeue_transcriptions,
)
from tests.factories import MeetingFactory
from tests.factories.deliverable_factory import DeliverableFactory


def _admin() -> Caller:
    return Caller(user_id=-1, keycloak_uuid=uuid.uuid4(), is_admin=True)


def _meeting_with_deliverable(
    meeting_status: MeetingStatus, deliverable_status: DeliverableStatus
) -> Meeting:
    meeting = MeetingFactory.create(
        status=meeting_status, name_platform=MeetingPlatforms.COMU
    )
    DeliverableFactory.create(
        meeting=meeting,
        type=DeliverableType.TRANSCRIPTION,
        status=deliverable_status,
        external_url=None,
    )
    return meeting


def _deliverable(meeting_id: int) -> Deliverable:
    return (
        get_db_session_ctx()
        .query(Deliverable)
        .filter(
            Deliverable.meeting_id == meeting_id,
            Deliverable.type == DeliverableType.TRANSCRIPTION,
            Deliverable.status != DeliverableStatus.DELETED,
        )
        .one()
    )


def test_all_requeueable_are_requeued(
    mock_celery_producer_app: Mock, db_session: Session
) -> None:
    in_progress = _meeting_with_deliverable(
        MeetingStatus.TRANSCRIPTION_IN_PROGRESS, DeliverableStatus.IN_PROGRESS
    )
    pending = _meeting_with_deliverable(
        MeetingStatus.TRANSCRIPTION_PENDING, DeliverableStatus.PENDING
    )
    failed = _meeting_with_deliverable(
        MeetingStatus.TRANSCRIPTION_FAILED, DeliverableStatus.FAILED
    )
    ids = [in_progress.id, pending.id, failed.id]

    result = requeue_transcriptions(ids, _admin())

    assert result.failed == []
    assert set(result.requeued) == set(ids)
    for meeting in (in_progress, pending, failed):
        db_session.refresh(meeting)
        assert meeting.status == MeetingStatus.TRANSCRIPTION_PENDING
        assert _deliverable(meeting.id).status == DeliverableStatus.PENDING
    assert mock_celery_producer_app.send_task.call_count == 3


def test_partial_success_reports_failures(
    mock_celery_producer_app: Mock, db_session: Session
) -> None:
    good = _meeting_with_deliverable(
        MeetingStatus.TRANSCRIPTION_FAILED, DeliverableStatus.FAILED
    )
    bad_state = _meeting_with_deliverable(
        MeetingStatus.TRANSCRIPTION_DONE, DeliverableStatus.AVAILABLE
    )
    unknown_id = 9_999_999

    result = requeue_transcriptions([good.id, bad_state.id, unknown_id], _admin())

    assert result.requeued == [good.id]
    assert (bad_state.id, RequeueReason.STATE_CONFLICT) in result.failed
    assert (unknown_id, RequeueReason.NOT_FOUND) in result.failed
    db_session.refresh(bad_state)
    assert bad_state.status == MeetingStatus.TRANSCRIPTION_DONE


def test_all_fail_dispatches_nothing(mock_celery_producer_app: Mock) -> None:
    bad_state = _meeting_with_deliverable(
        MeetingStatus.TRANSCRIPTION_DONE, DeliverableStatus.AVAILABLE
    )

    result = requeue_transcriptions([bad_state.id, 9_999_999], _admin())

    assert result.requeued == []
    assert {reason for _, reason in result.failed} == {
        RequeueReason.STATE_CONFLICT,
        RequeueReason.NOT_FOUND,
    }
    mock_celery_producer_app.send_task.assert_not_called()


def test_deduplicates_is_left_to_router_but_loop_is_idempotent_per_id(
    mock_celery_producer_app: Mock,
) -> None:
    # The use-case itself processes each id it is given; the router dedupes.
    # A single failed meeting requeued once ends up PENDING.
    failed = _meeting_with_deliverable(
        MeetingStatus.TRANSCRIPTION_FAILED, DeliverableStatus.FAILED
    )

    result = requeue_transcriptions([failed.id], _admin())

    assert result.requeued == [failed.id]


def test_per_meeting_isolation_on_dispatch_failure(
    mock_celery_producer_app: Mock, db_session: Session, mocker: MockerFixture
) -> None:
    good = _meeting_with_deliverable(
        MeetingStatus.TRANSCRIPTION_FAILED, DeliverableStatus.FAILED
    )
    doomed = _meeting_with_deliverable(
        MeetingStatus.TRANSCRIPTION_IN_PROGRESS, DeliverableStatus.IN_PROGRESS
    )

    real_dispatch = uc.dispatch_transcription_task

    def flaky_dispatch(meeting_id: int, owner_keycloak_uuid: str) -> None:
        if meeting_id == doomed.id:
            raise RuntimeError("broker down")
        real_dispatch(meeting_id, owner_keycloak_uuid)

    mocker.patch.object(uc, "dispatch_transcription_task", side_effect=flaky_dispatch)

    result = requeue_transcriptions([good.id, doomed.id], _admin())

    assert result.requeued == [good.id]
    assert (doomed.id, RequeueReason.INTERNAL) in result.failed
    db_session.refresh(good)
    db_session.refresh(doomed)
    assert good.status == MeetingStatus.TRANSCRIPTION_PENDING
    # doomed rolled back to its pre-call state; no transient FAILED persisted.
    assert doomed.status == MeetingStatus.TRANSCRIPTION_IN_PROGRESS
    assert _deliverable(doomed.id).status == DeliverableStatus.IN_PROGRESS


def test_non_owner_non_admin_collapses_to_not_found(
    mock_celery_producer_app: Mock,
) -> None:
    meeting = _meeting_with_deliverable(
        MeetingStatus.TRANSCRIPTION_FAILED, DeliverableStatus.FAILED
    )
    other_user = Caller(
        user_id=meeting.user_id + 1000, keycloak_uuid=uuid.uuid4(), is_admin=False
    )

    result = requeue_transcriptions([meeting.id], other_user)

    assert result.requeued == []
    assert result.failed == [(meeting.id, RequeueReason.NOT_FOUND)]
    mock_celery_producer_app.send_task.assert_not_called()
