import pytest

from mcr_meeting.app.domain.deliverable_transitions import (
    mark_available,
    mark_failed,
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


class TestMarkAvailable:
    def test_flips_pending_to_available(self) -> None:
        deliverable = _make_deliverable(DeliverableStatus.PENDING)

        result = mark_available(deliverable, external_url=None)

        assert result is deliverable
        assert deliverable.status == DeliverableStatus.AVAILABLE

    def test_sets_external_url(self) -> None:
        deliverable = _make_deliverable(DeliverableStatus.PENDING)

        mark_available(deliverable, external_url="https://drive.example.com/x")

        assert deliverable.external_url == "https://drive.example.com/x"

    def test_keeps_external_url_none_when_none_passed(self) -> None:
        deliverable = _make_deliverable(DeliverableStatus.PENDING)

        mark_available(deliverable, external_url=None)

        assert deliverable.external_url is None

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
    def test_flips_pending_to_failed(self) -> None:
        deliverable = _make_deliverable(DeliverableStatus.PENDING)

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
            DeliverableStatus.PENDING,
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
