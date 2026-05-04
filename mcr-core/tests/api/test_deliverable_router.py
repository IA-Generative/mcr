from io import BytesIO
from typing import Any
from unittest.mock import MagicMock, Mock

import pytest
from fastapi.testclient import TestClient

from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.app.models.deliverable_model import (
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.meeting_model import (
    MeetingPlatforms,
    MeetingStatus,
)
from mcr_meeting.app.models.user_model import User
from mcr_meeting.main import app
from tests.api.conftest import PrefixedTestClient
from tests.factories import MeetingFactory, UserFactory
from tests.factories.deliverable_factory import DeliverableFactory

api_settings = ApiSettings()


@pytest.fixture
def deliverables_client() -> PrefixedTestClient:
    return PrefixedTestClient(TestClient(app), api_settings.DELIVERABLE_API_PREFIX)


def _decision_record_body() -> dict[str, Any]:
    return {
        "header": {
            "title": "Title",
            "objective": None,
            "participants": [],
            "next_meeting": None,
        },
        "topics_with_decision": [],
        "next_steps": [],
    }


class TestListDeliverablesRoute:
    def test_returns_rows_for_owner(
        self,
        meeting_client: PrefixedTestClient,
        user_fixture: User,
    ) -> None:
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.REPORT_DONE,
            name_platform=MeetingPlatforms.COMU,
        )
        DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.AVAILABLE,
        )
        DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.TRANSCRIPTION,
            status=DeliverableStatus.AVAILABLE,
        )
        DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DETAILED_SYNTHESIS,
            status=DeliverableStatus.DELETED,
        )

        response = meeting_client.get(
            f"/{meeting.id}/deliverables",
            headers={"X-User-Keycloak-UUID": str(user_fixture.keycloak_uuid)},
        )

        assert response.status_code == 200
        body = response.json()
        types = {row["type"] for row in body["deliverables"]}
        assert types == {"DECISION_RECORD", "TRANSCRIPTION"}
        assert all("id" in row for row in body["deliverables"])
        assert all("status" in row for row in body["deliverables"])

    def test_404_for_unknown_meeting(
        self,
        meeting_client: PrefixedTestClient,
        user_fixture: User,
    ) -> None:
        response = meeting_client.get(
            "/999999/deliverables",
            headers={"X-User-Keycloak-UUID": str(user_fixture.keycloak_uuid)},
        )
        assert response.status_code == 404

    def test_403_for_non_owner(
        self,
        meeting_client: PrefixedTestClient,
        user_fixture: User,
    ) -> None:
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.REPORT_DONE,
            name_platform=MeetingPlatforms.COMU,
        )
        intruder = UserFactory.create()

        response = meeting_client.get(
            f"/{meeting.id}/deliverables",
            headers={"X-User-Keycloak-UUID": str(intruder.keycloak_uuid)},
        )

        assert response.status_code == 403


class TestPostDeliverableRoute:
    def test_returns_202_with_row_json(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
        mock_celery_producer_app: Mock,
    ) -> None:
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )

        response = deliverables_client.post(
            "",
            json={"meeting_id": meeting.id, "type": "DECISION_RECORD"},
            headers={"X-User-Keycloak-UUID": str(user_fixture.keycloak_uuid)},
        )

        assert response.status_code == 202
        body = response.json()
        assert body["type"] == "DECISION_RECORD"
        assert body["status"] == "PENDING"
        assert body["meeting_id"] == meeting.id
        assert "id" in body

    def test_400_for_transcription_type(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
        mock_celery_producer_app: Mock,
    ) -> None:
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )

        response = deliverables_client.post(
            "",
            json={"meeting_id": meeting.id, "type": "TRANSCRIPTION"},
            headers={"X-User-Keycloak-UUID": str(user_fixture.keycloak_uuid)},
        )

        assert response.status_code == 400
        mock_celery_producer_app.send_task.assert_not_called()

    def test_dispatches_celery_task_with_deliverable_id(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
        mock_celery_producer_app: Mock,
    ) -> None:
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )

        response = deliverables_client.post(
            "",
            json={"meeting_id": meeting.id, "type": "DECISION_RECORD"},
            headers={"X-User-Keycloak-UUID": str(user_fixture.keycloak_uuid)},
        )

        deliverable_id = response.json()["id"]

        mock_celery_producer_app.send_task.assert_called_once()
        call = mock_celery_producer_app.send_task.call_args
        assert call.kwargs["args"][0] == meeting.id
        assert call.kwargs["args"][2] == "DECISION_RECORD"
        assert call.kwargs["kwargs"] == {
            "owner_keycloak_uuid": str(user_fixture.keycloak_uuid),
            "deliverable_id": deliverable_id,
        }


class TestSuccessCallbackRoute:
    def test_flips_to_available(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
        mock_send_email: MagicMock,
        mock_persist_report_docx: MagicMock,
        db_session: Any,
    ) -> None:
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
        )
        pending = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.PENDING,
        )

        response = deliverables_client.post(
            f"/{pending.id}/success",
            json={
                "external_url": "https://drive.example.com/abc",
                "report_response": _decision_record_body(),
            },
        )

        assert response.status_code == 200
        db_session.refresh(pending)
        db_session.refresh(meeting)
        assert pending.status == DeliverableStatus.AVAILABLE
        assert pending.external_url == "https://drive.example.com/abc"
        assert meeting.status == MeetingStatus.REPORT_DONE
        mock_persist_report_docx.assert_called_once()


class TestFailureCallbackRoute:
    def test_flips_to_failed(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
        db_session: Any,
    ) -> None:
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
        )
        pending = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.PENDING,
        )

        response = deliverables_client.post(f"/{pending.id}/failure")

        assert response.status_code == 200
        db_session.refresh(pending)
        db_session.refresh(meeting)
        assert pending.status == DeliverableStatus.FAILED
        assert meeting.status == MeetingStatus.REPORT_FAILED


class TestDeleteRoute:
    def test_returns_204_and_soft_deletes(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
        db_session: Any,
    ) -> None:
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.REPORT_DONE,
            name_platform=MeetingPlatforms.COMU,
            report_filename="report.docx",
        )
        deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.AVAILABLE,
        )

        response = deliverables_client.delete(
            f"/{deliverable.id}",
            headers={"X-User-Keycloak-UUID": str(user_fixture.keycloak_uuid)},
        )

        assert response.status_code == 204
        db_session.refresh(deliverable)
        assert deliverable.status == DeliverableStatus.DELETED
        db_session.refresh(meeting)
        assert meeting.status == MeetingStatus.TRANSCRIPTION_DONE


class TestGetFileRoute:
    def test_streams_typed_docx_from_s3(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
        mocker: Any,
    ) -> None:
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.REPORT_DONE,
            name_platform=MeetingPlatforms.COMU,
            report_filename="decision_record.docx",
        )
        deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.AVAILABLE,
        )
        mocker.patch(
            "mcr_meeting.app.orchestrators.deliverable_orchestrator.get_typed_deliverable_from_s3",
            return_value=BytesIO(b"typed docx content"),
        )

        response = deliverables_client.get(
            f"/{deliverable.id}/file",
            headers={"X-User-Keycloak-UUID": str(user_fixture.keycloak_uuid)},
        )

        assert response.status_code == 200
        assert (
            response.headers["content-type"]
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert "attachment" in response.headers["content-disposition"]
        assert response.content == b"typed docx content"

    def test_falls_back_to_legacy_filename_when_typed_missing(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
        mocker: Any,
    ) -> None:
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.REPORT_DONE,
            name_platform=MeetingPlatforms.COMU,
            report_filename="report.docx",
        )
        deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.AVAILABLE,
        )
        mocker.patch(
            "mcr_meeting.app.orchestrators.deliverable_orchestrator.get_typed_deliverable_from_s3",
            return_value=None,
        )
        mocker.patch(
            "mcr_meeting.app.orchestrators.deliverable_orchestrator.get_formatted_report_from_s3",
            return_value=BytesIO(b"legacy docx content"),
        )

        response = deliverables_client.get(
            f"/{deliverable.id}/file",
            headers={"X-User-Keycloak-UUID": str(user_fixture.keycloak_uuid)},
        )

        assert response.status_code == 200
        assert response.content == b"legacy docx content"
