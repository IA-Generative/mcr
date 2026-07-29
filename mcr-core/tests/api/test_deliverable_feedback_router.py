import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.app.models.deliverable_feedback_model import DeliverableFeedback
from mcr_meeting.app.models.deliverable_model import DeliverableStatus, DeliverableType
from mcr_meeting.app.models.feedback_model import VoteType
from mcr_meeting.app.models.meeting_model import MeetingPlatforms, MeetingStatus
from mcr_meeting.app.models.user_model import User
from mcr_meeting.main import app
from tests.api.conftest import PrefixedTestClient
from tests.factories import MeetingFactory, UserFactory
from tests.factories.deliverable_factory import DeliverableFactory
from tests.factories.deliverable_feedback_factory import DeliverableFeedbackFactory

api_settings = ApiSettings()


@pytest.fixture
def deliverables_client() -> PrefixedTestClient:
    return PrefixedTestClient(TestClient(app), api_settings.DELIVERABLE_API_PREFIX)


def _owned_deliverable(
    owner: User, status: DeliverableStatus = DeliverableStatus.AVAILABLE
) -> Any:
    meeting = MeetingFactory.create(
        owner=owner,
        status=MeetingStatus.REPORT_DONE,
        name_platform=MeetingPlatforms.COMU,
    )
    return DeliverableFactory.create(
        meeting=meeting, type=DeliverableType.DECISION_RECORD, status=status
    )


def _headers(user: User) -> dict[str, str]:
    return {"x-user-keycloak-uuid": str(user.keycloak_uuid)}


class TestUpsertDeliverableFeedback:
    def test_a_submitted_vote_is_published_on_the_meeting_deliverables(
        self,
        deliverables_client: PrefixedTestClient,
        meeting_client: PrefixedTestClient,
        user_fixture: User,
    ) -> None:
        deliverable = _owned_deliverable(user_fixture)

        put = deliverables_client.put(
            f"/{deliverable.id}/feedback",
            json={"vote_type": "POSITIVE", "comment": "clear and faithful"},
            headers=_headers(user_fixture),
        )

        assert put.status_code == 200
        assert put.json() == {"vote_type": "POSITIVE", "comment": "clear and faithful"}

        listed = meeting_client.get(
            f"/{deliverable.meeting_id}/deliverables", headers=_headers(user_fixture)
        )
        assert listed.status_code == 200
        (row,) = listed.json()["deliverables"]
        assert row["feedback"] == {
            "vote_type": "POSITIVE",
            "comment": "clear and faithful",
        }

    def test_a_positive_vote_needs_no_comment(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
    ) -> None:
        deliverable = _owned_deliverable(user_fixture)

        response = deliverables_client.put(
            f"/{deliverable.id}/feedback",
            json={"vote_type": "POSITIVE"},
            headers=_headers(user_fixture),
        )

        assert response.status_code == 200
        assert response.json() == {"vote_type": "POSITIVE", "comment": None}

    def test_voting_twice_replaces_the_previous_opinion(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
        db_session: Session,
    ) -> None:
        deliverable = _owned_deliverable(user_fixture)

        deliverables_client.put(
            f"/{deliverable.id}/feedback",
            json={"vote_type": "POSITIVE", "comment": "first"},
            headers=_headers(user_fixture),
        )
        second = deliverables_client.put(
            f"/{deliverable.id}/feedback",
            json={"vote_type": "POSITIVE", "comment": "second"},
            headers=_headers(user_fixture),
        )

        assert second.status_code == 200
        assert second.json()["comment"] == "second"
        assert (
            db_session.query(DeliverableFeedback)
            .filter(DeliverableFeedback.deliverable_id == deliverable.id)
            .count()
            == 1
        )

    @pytest.mark.parametrize("comment", [None, "", "   "])
    def test_a_negative_vote_without_a_comment_is_refused(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
        db_session: Session,
        comment: str | None,
    ) -> None:
        deliverable = _owned_deliverable(user_fixture)

        response = deliverables_client.put(
            f"/{deliverable.id}/feedback",
            json={"vote_type": "NEGATIVE", "comment": comment},
            headers=_headers(user_fixture),
        )

        assert response.status_code == 422
        assert (
            db_session.query(DeliverableFeedback)
            .filter(DeliverableFeedback.deliverable_id == deliverable.id)
            .count()
            == 0
        )

    def test_a_reasons_field_is_rejected_rather_than_silently_dropped(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
    ) -> None:
        deliverable = _owned_deliverable(user_fixture)

        response = deliverables_client.put(
            f"/{deliverable.id}/feedback",
            json={
                "vote_type": "POSITIVE",
                "comment": "good",
                "reasons": ["MISSING_INFORMATION"],
            },
            headers=_headers(user_fixture),
        )

        assert response.status_code == 422

    @pytest.mark.parametrize(
        "status",
        [
            DeliverableStatus.REQUESTED,
            DeliverableStatus.PENDING,
            DeliverableStatus.IN_PROGRESS,
            DeliverableStatus.FAILED,
        ],
    )
    def test_a_deliverable_that_is_not_available_cannot_be_rated(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
        status: DeliverableStatus,
    ) -> None:
        deliverable = _owned_deliverable(user_fixture, status=status)

        response = deliverables_client.put(
            f"/{deliverable.id}/feedback",
            json={"vote_type": "POSITIVE"},
            headers=_headers(user_fixture),
        )

        assert response.status_code == 400

    def test_rating_someone_elses_deliverable_does_not_disclose_it_exists(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
    ) -> None:
        deliverable = _owned_deliverable(user_fixture)
        intruder = UserFactory.create(keycloak_uuid=uuid.uuid4())

        response = deliverables_client.put(
            f"/{deliverable.id}/feedback",
            json={"vote_type": "POSITIVE"},
            headers=_headers(intruder),
        )

        assert response.status_code == 404

    def test_rating_an_unknown_deliverable_is_not_found(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
    ) -> None:
        response = deliverables_client.put(
            "/999999/feedback",
            json={"vote_type": "POSITIVE"},
            headers=_headers(user_fixture),
        )

        assert response.status_code == 404


class TestDeactivateDeliverableFeedback:
    def test_a_retracted_vote_disappears_from_the_api_but_stays_in_the_database(
        self,
        deliverables_client: PrefixedTestClient,
        meeting_client: PrefixedTestClient,
        user_fixture: User,
        db_session: Session,
    ) -> None:
        deliverable = _owned_deliverable(user_fixture)
        DeliverableFeedbackFactory.create(
            deliverable=deliverable,
            vote_type=VoteType.POSITIVE,
            comment="kept for the dashboards",
        )
        db_session.commit()

        response = deliverables_client.delete(
            f"/{deliverable.id}/feedback", headers=_headers(user_fixture)
        )

        assert response.status_code == 204

        listed = meeting_client.get(
            f"/{deliverable.meeting_id}/deliverables", headers=_headers(user_fixture)
        )
        (row,) = listed.json()["deliverables"]
        assert row["feedback"] is None

        stored = (
            db_session.query(DeliverableFeedback)
            .filter(DeliverableFeedback.deliverable_id == deliverable.id)
            .one()
        )
        assert stored.is_active is False
        assert stored.comment == "kept for the dashboards"

    def test_retracting_twice_is_idempotent(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
        db_session: Session,
    ) -> None:
        deliverable = _owned_deliverable(user_fixture)
        DeliverableFeedbackFactory.create(deliverable=deliverable)
        db_session.commit()

        first = deliverables_client.delete(
            f"/{deliverable.id}/feedback", headers=_headers(user_fixture)
        )
        second = deliverables_client.delete(
            f"/{deliverable.id}/feedback", headers=_headers(user_fixture)
        )

        assert (first.status_code, second.status_code) == (204, 204)

    def test_retracting_a_vote_that_was_never_cast_succeeds(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
    ) -> None:
        deliverable = _owned_deliverable(user_fixture)

        response = deliverables_client.delete(
            f"/{deliverable.id}/feedback", headers=_headers(user_fixture)
        )

        assert response.status_code == 204

    def test_voting_again_after_retracting_republishes_the_opinion(
        self,
        deliverables_client: PrefixedTestClient,
        meeting_client: PrefixedTestClient,
        user_fixture: User,
    ) -> None:
        deliverable = _owned_deliverable(user_fixture)
        deliverables_client.put(
            f"/{deliverable.id}/feedback",
            json={"vote_type": "POSITIVE", "comment": "nice"},
            headers=_headers(user_fixture),
        )
        deliverables_client.delete(
            f"/{deliverable.id}/feedback", headers=_headers(user_fixture)
        )

        deliverables_client.put(
            f"/{deliverable.id}/feedback",
            json={"vote_type": "POSITIVE", "comment": "still nice"},
            headers=_headers(user_fixture),
        )

        listed = meeting_client.get(
            f"/{deliverable.meeting_id}/deliverables", headers=_headers(user_fixture)
        )
        (row,) = listed.json()["deliverables"]
        assert row["feedback"] == {"vote_type": "POSITIVE", "comment": "still nice"}

    def test_retracting_someone_elses_vote_does_not_disclose_the_deliverable(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
        db_session: Session,
    ) -> None:
        deliverable = _owned_deliverable(user_fixture)
        DeliverableFeedbackFactory.create(deliverable=deliverable)
        db_session.commit()
        intruder = UserFactory.create(keycloak_uuid=uuid.uuid4())

        response = deliverables_client.delete(
            f"/{deliverable.id}/feedback", headers=_headers(intruder)
        )

        assert response.status_code == 404


def test_a_published_feedback_exposes_nothing_beyond_the_vote_and_its_comment(
    deliverables_client: PrefixedTestClient,
    meeting_client: PrefixedTestClient,
    user_fixture: User,
) -> None:
    deliverable = _owned_deliverable(user_fixture)
    put = deliverables_client.put(
        f"/{deliverable.id}/feedback",
        json={"vote_type": "POSITIVE"},
        headers=_headers(user_fixture),
    )

    listed = meeting_client.get(
        f"/{deliverable.meeting_id}/deliverables", headers=_headers(user_fixture)
    )
    (row,) = listed.json()["deliverables"]

    assert set(put.json()) == {"vote_type", "comment"}
    assert set(row["feedback"]) == {"vote_type", "comment"}
