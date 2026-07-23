import uuid
from collections.abc import Iterator
from unittest.mock import Mock

import pytest

from mcr_meeting.app.api.dependencies.auth import require_admin
from mcr_meeting.app.models.deliverable_model import (
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.meeting_model import (
    Meeting,
    MeetingPlatforms,
    MeetingStatus,
)
from mcr_meeting.app.schemas.caller_schema import Caller
from mcr_meeting.main import app
from tests.api.conftest import PrefixedTestClient, TestClient, api_settings
from tests.factories import MeetingFactory
from tests.factories.deliverable_factory import DeliverableFactory


@pytest.fixture
def admin_requeue_client() -> Iterator[PrefixedTestClient]:
    app.dependency_overrides[require_admin] = lambda: Caller(
        user_id=-1, keycloak_uuid=uuid.uuid4(), is_admin=True
    )
    try:
        yield PrefixedTestClient(TestClient(app), api_settings.MEETING_API_PREFIX)
    finally:
        app.dependency_overrides.pop(require_admin, None)


def _requeueable_meeting() -> Meeting:
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_FAILED,
        name_platform=MeetingPlatforms.COMU,
    )
    DeliverableFactory.create(
        meeting=meeting,
        type=DeliverableType.TRANSCRIPTION,
        status=DeliverableStatus.FAILED,
        external_url=None,
    )
    return meeting


def test_all_requeued_returns_202(
    admin_requeue_client: PrefixedTestClient, mock_celery_producer_app: Mock
) -> None:
    meeting = _requeueable_meeting()

    response = admin_requeue_client.post(
        "/transcription/requeue", json={"meeting_ids": [meeting.id]}
    )

    assert response.status_code == 202
    assert response.json() == {"requeued": [meeting.id], "failed": []}


def test_mixed_outcome_returns_207(
    admin_requeue_client: PrefixedTestClient, mock_celery_producer_app: Mock
) -> None:
    good = _requeueable_meeting()

    response = admin_requeue_client.post(
        "/transcription/requeue", json={"meeting_ids": [good.id, 9_999_999]}
    )

    assert response.status_code == 207
    body = response.json()
    assert body["requeued"] == [good.id]
    assert body["failed"] == [{"meeting_id": 9_999_999, "reason": "NOT_FOUND"}]


def test_duplicate_ids_are_deduped(
    admin_requeue_client: PrefixedTestClient, mock_celery_producer_app: Mock
) -> None:
    meeting = _requeueable_meeting()

    response = admin_requeue_client.post(
        "/transcription/requeue", json={"meeting_ids": [meeting.id, meeting.id]}
    )

    assert response.status_code == 202
    assert response.json()["requeued"] == [meeting.id]
    assert mock_celery_producer_app.send_task.call_count == 1


def test_empty_meeting_ids_is_422(
    admin_requeue_client: PrefixedTestClient,
) -> None:
    response = admin_requeue_client.post(
        "/transcription/requeue", json={"meeting_ids": []}
    )
    assert response.status_code == 422


def test_too_many_meeting_ids_is_422(
    admin_requeue_client: PrefixedTestClient,
) -> None:
    response = admin_requeue_client.post(
        "/transcription/requeue", json={"meeting_ids": list(range(1, 102))}
    )
    assert response.status_code == 422


def test_missing_bearer_is_401() -> None:
    client = PrefixedTestClient(TestClient(app), api_settings.MEETING_API_PREFIX)
    response = client.post("/transcription/requeue", json={"meeting_ids": [1]})
    assert response.status_code == 401
