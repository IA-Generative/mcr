import pytest

from mcr_meeting.app.domain.deliverable_transitions import (
    dispatch,
    forced_requeue,
    mark_available,
    mark_failed,
    mark_in_progress,
    soft_delete,
)
from mcr_meeting.app.exceptions.exceptions import DeliverableStateConflictException
from mcr_meeting.app.models.deliverable_model import (
    Deliverable,
    DeliverableStatus,
    DeliverableType,
)


def _make_deliverable(status: DeliverableStatus) -> Deliverable:
    return Deliverable(
        meeting_id=1,
        type=DeliverableType.DECISION_RECORD,
        status=status,
    )


class TestDispatch:
    def test_flips_requested_to_pending(self) -> None:
        deliverable = _make_deliverable(DeliverableStatus.REQUESTED)

        result = dispatch(deliverable)

        assert result is deliverable
        assert deliverable.status == DeliverableStatus.PENDING

    @pytest.mark.parametrize(
        "starting_status",
        [
            DeliverableStatus.PENDING,
            DeliverableStatus.IN_PROGRESS,
            DeliverableStatus.AVAILABLE,
            DeliverableStatus.FAILED,
            DeliverableStatus.DELETED,
        ],
    )
    def test_rejects_from_any_other_status(
        self, starting_status: DeliverableStatus
    ) -> None:
        deliverable = _make_deliverable(starting_status)

        with pytest.raises(DeliverableStateConflictException):
            dispatch(deliverable)

        assert deliverable.status == starting_status


class TestMarkInProgress:
    def test_flips_pending_to_in_progress(self) -> None:
        deliverable = _make_deliverable(DeliverableStatus.PENDING)

        result = mark_in_progress(deliverable)

        assert result is deliverable
        assert deliverable.status == DeliverableStatus.IN_PROGRESS

    @pytest.mark.parametrize(
        "starting_status",
        [
            DeliverableStatus.REQUESTED,
            DeliverableStatus.IN_PROGRESS,
            DeliverableStatus.AVAILABLE,
            DeliverableStatus.FAILED,
            DeliverableStatus.DELETED,
        ],
    )
    def test_rejects_from_any_other_status(
        self, starting_status: DeliverableStatus
    ) -> None:
        deliverable = _make_deliverable(starting_status)

        with pytest.raises(DeliverableStateConflictException):
            mark_in_progress(deliverable)

        assert deliverable.status == starting_status


class TestForcedRequeue:
    @pytest.mark.parametrize(
        "starting_status",
        [DeliverableStatus.IN_PROGRESS, DeliverableStatus.FAILED],
    )
    def test_flips_requeueable_back_to_pending(
        self, starting_status: DeliverableStatus
    ) -> None:
        deliverable = _make_deliverable(starting_status)

        result = forced_requeue(deliverable)

        assert result is deliverable
        assert deliverable.status == DeliverableStatus.PENDING

    def test_pending_self_loop_is_a_noop(self) -> None:
        deliverable = _make_deliverable(DeliverableStatus.PENDING)

        forced_requeue(deliverable)

        assert deliverable.status == DeliverableStatus.PENDING

    @pytest.mark.parametrize(
        "starting_status",
        [
            DeliverableStatus.REQUESTED,
            DeliverableStatus.AVAILABLE,
            DeliverableStatus.DELETED,
        ],
    )
    def test_rejects_from_non_requeueable_status(
        self, starting_status: DeliverableStatus
    ) -> None:
        deliverable = _make_deliverable(starting_status)

        with pytest.raises(DeliverableStateConflictException):
            forced_requeue(deliverable)

        assert deliverable.status == starting_status


class TestMarkAvailable:
    def test_sets_external_url(self) -> None:
        deliverable = _make_deliverable(DeliverableStatus.IN_PROGRESS)

        mark_available(deliverable, external_url="https://drive.example.com/x")

        assert deliverable.external_url == "https://drive.example.com/x"

    def test_keeps_external_url_none_when_none_passed(self) -> None:
        deliverable = _make_deliverable(DeliverableStatus.IN_PROGRESS)

        mark_available(deliverable, external_url=None)

        assert deliverable.external_url is None

    def test_flips_in_progress_to_available(self) -> None:
        deliverable = _make_deliverable(DeliverableStatus.IN_PROGRESS)

        mark_available(deliverable, external_url=None)

        assert deliverable.status == DeliverableStatus.AVAILABLE

    def test_rejects_from_pending(self) -> None:
        deliverable = _make_deliverable(DeliverableStatus.PENDING)

        with pytest.raises(DeliverableStateConflictException):
            mark_available(deliverable, external_url=None)

        assert deliverable.status == DeliverableStatus.PENDING

    def test_rejects_already_available(self) -> None:
        deliverable = _make_deliverable(DeliverableStatus.AVAILABLE)

        with pytest.raises(DeliverableStateConflictException):
            mark_available(deliverable, external_url=None)

        assert deliverable.status == DeliverableStatus.AVAILABLE

    def test_rejects_from_failed(self) -> None:
        deliverable = _make_deliverable(DeliverableStatus.FAILED)

        with pytest.raises(DeliverableStateConflictException):
            mark_available(deliverable, external_url=None)

    def test_rejects_from_deleted(self) -> None:
        deliverable = _make_deliverable(DeliverableStatus.DELETED)

        with pytest.raises(DeliverableStateConflictException):
            mark_available(deliverable, external_url=None)


class TestMarkFailed:
    def test_flips_requested_to_failed(self) -> None:
        deliverable = _make_deliverable(DeliverableStatus.REQUESTED)

        mark_failed(deliverable)

        assert deliverable.status == DeliverableStatus.FAILED

    def test_flips_pending_to_failed(self) -> None:
        deliverable = _make_deliverable(DeliverableStatus.PENDING)

        mark_failed(deliverable)

        assert deliverable.status == DeliverableStatus.FAILED

    def test_flips_in_progress_to_failed(self) -> None:
        deliverable = _make_deliverable(DeliverableStatus.IN_PROGRESS)

        mark_failed(deliverable)

        assert deliverable.status == DeliverableStatus.FAILED

    def test_rejects_from_available(self) -> None:
        deliverable = _make_deliverable(DeliverableStatus.AVAILABLE)

        with pytest.raises(DeliverableStateConflictException):
            mark_failed(deliverable)


class TestSoftDelete:
    @pytest.mark.parametrize(
        "starting_status",
        [
            DeliverableStatus.REQUESTED,
            DeliverableStatus.PENDING,
            DeliverableStatus.IN_PROGRESS,
            DeliverableStatus.AVAILABLE,
            DeliverableStatus.FAILED,
        ],
    )
    def test_allowed_from_any_active_status(
        self, starting_status: DeliverableStatus
    ) -> None:
        deliverable = _make_deliverable(starting_status)

        soft_delete(deliverable)

        assert deliverable.status == DeliverableStatus.DELETED

    def test_rejects_from_deleted(self) -> None:
        deliverable = _make_deliverable(DeliverableStatus.DELETED)

        with pytest.raises(DeliverableStateConflictException):
            soft_delete(deliverable)
