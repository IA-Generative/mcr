from io import BytesIO
from typing import Any
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.app.infrastructure.redis import get_refresh_token, save_refresh_token
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
from tests.mocks.in_memory_drive import InMemoryDriveClient
from tests.mocks.in_memory_email import InMemoryEmailClient
from tests.mocks.in_memory_keycloak import InMemoryKeycloak
from tests.mocks.in_memory_s3 import InMemoryS3

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
        DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.TRANSCRIPTION,
            status=DeliverableStatus.AVAILABLE,
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

    def test_422_for_standard_type_with_custom_prompt(
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
        DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.TRANSCRIPTION,
            status=DeliverableStatus.AVAILABLE,
        )

        response = deliverables_client.post(
            "",
            json={
                "meeting_id": meeting.id,
                "type": "DETAILED_SYNTHESIS",
                "custom_prompt": "Un prompt qui ne devrait pas être accepté",
            },
            headers={"X-User-Keycloak-UUID": str(user_fixture.keycloak_uuid)},
        )

        assert response.status_code == 422
        mock_celery_producer_app.send_task.assert_not_called()

    def test_422_for_transcription_type(
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
        DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.TRANSCRIPTION,
            status=DeliverableStatus.AVAILABLE,
        )

        response = deliverables_client.post(
            "",
            json={"meeting_id": meeting.id, "type": "TRANSCRIPTION"},
            headers={"X-User-Keycloak-UUID": str(user_fixture.keycloak_uuid)},
        )

        assert response.status_code == 422
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
        DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.TRANSCRIPTION,
            status=DeliverableStatus.AVAILABLE,
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

    def test_stores_offline_token_when_access_token_header_provided(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
        in_memory_keycloak: InMemoryKeycloak,
        mock_celery_producer_app: Mock,
    ) -> None:
        in_memory_keycloak.exchange_refresh_token = "offline-refresh-token"
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )
        DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.TRANSCRIPTION,
            status=DeliverableStatus.AVAILABLE,
        )

        response = deliverables_client.post(
            "",
            json={"meeting_id": meeting.id, "type": "DECISION_RECORD"},
            headers={
                "X-User-Keycloak-UUID": str(user_fixture.keycloak_uuid),
                "X-User-Access-Token": "user-access-token",
            },
        )

        assert response.status_code == 202
        assert (
            get_refresh_token(str(user_fixture.keycloak_uuid))
            == "offline-refresh-token"
        )

    def test_returns_202_without_access_token_header(
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
        DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.TRANSCRIPTION,
            status=DeliverableStatus.AVAILABLE,
        )

        response = deliverables_client.post(
            "",
            json={"meeting_id": meeting.id, "type": "DECISION_RECORD"},
            headers={"X-User-Keycloak-UUID": str(user_fixture.keycloak_uuid)},
        )

        assert response.status_code == 202
        assert get_refresh_token(str(user_fixture.keycloak_uuid)) is None


class TestPostCustomReportRoute:
    def test_returns_202_for_custom_report_with_prompt(
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
        DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.TRANSCRIPTION,
            status=DeliverableStatus.AVAILABLE,
        )

        response = deliverables_client.post(
            "",
            json={
                "meeting_id": meeting.id,
                "type": "CUSTOM_REPORT",
                "custom_prompt": "Résume les décisions clés",
            },
            headers={"X-User-Keycloak-UUID": str(user_fixture.keycloak_uuid)},
        )

        assert response.status_code == 202
        body = response.json()
        assert body["type"] == "CUSTOM_REPORT"
        assert body["status"] == "PENDING"

    def test_422_for_custom_report_without_prompt(
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
        DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.TRANSCRIPTION,
            status=DeliverableStatus.AVAILABLE,
        )

        response = deliverables_client.post(
            "",
            json={"meeting_id": meeting.id, "type": "CUSTOM_REPORT"},
            headers={"X-User-Keycloak-UUID": str(user_fixture.keycloak_uuid)},
        )

        assert response.status_code == 422
        mock_celery_producer_app.send_task.assert_not_called()

    def test_422_for_custom_report_with_empty_prompt(
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
        DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.TRANSCRIPTION,
            status=DeliverableStatus.AVAILABLE,
        )

        response = deliverables_client.post(
            "",
            json={
                "meeting_id": meeting.id,
                "type": "CUSTOM_REPORT",
                "custom_prompt": "",
            },
            headers={"X-User-Keycloak-UUID": str(user_fixture.keycloak_uuid)},
        )

        assert response.status_code == 422
        mock_celery_producer_app.send_task.assert_not_called()

    def test_dispatches_celery_task_with_custom_prompt(
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
        DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.TRANSCRIPTION,
            status=DeliverableStatus.AVAILABLE,
        )

        response = deliverables_client.post(
            "",
            json={
                "meeting_id": meeting.id,
                "type": "CUSTOM_REPORT",
                "custom_prompt": "Analyse les risques",
            },
            headers={"X-User-Keycloak-UUID": str(user_fixture.keycloak_uuid)},
        )

        deliverable_id = response.json()["id"]

        mock_celery_producer_app.send_task.assert_called_once()
        call = mock_celery_producer_app.send_task.call_args
        assert call.kwargs["args"][2] == "CUSTOM_REPORT"
        assert call.kwargs["kwargs"] == {
            "owner_keycloak_uuid": str(user_fixture.keycloak_uuid),
            "deliverable_id": deliverable_id,
            "custom_prompt": "Analyse les risques",
        }


class TestInProgressCallbackRoute:
    def test_flips_pending_to_in_progress(
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
        pending_deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.PENDING,
        )

        response = deliverables_client.post(f"/{pending_deliverable.id}/start")

        assert response.status_code == 200
        assert response.json()["status"] == "IN_PROGRESS"
        db_session.refresh(pending_deliverable)
        db_session.refresh(meeting)
        assert pending_deliverable.status == DeliverableStatus.IN_PROGRESS
        assert meeting.status == MeetingStatus.REPORT_PENDING

    def test_409_when_already_in_progress(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
    ) -> None:
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
        )
        in_progress_deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.IN_PROGRESS,
        )

        response = deliverables_client.post(f"/{in_progress_deliverable.id}/start")

        assert response.status_code == 409

    def test_425_when_still_requested(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
    ) -> None:
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.TRANSCRIPTION_IN_PROGRESS,
            name_platform=MeetingPlatforms.COMU,
        )
        requested_deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.REQUESTED,
        )

        response = deliverables_client.post(f"/{requested_deliverable.id}/start")

        assert response.status_code == 425

    def test_404_for_unknown_deliverable(
        self,
        deliverables_client: PrefixedTestClient,
    ) -> None:
        response = deliverables_client.post("/999999/start")

        assert response.status_code == 404


class TestSuccessCallbackRoute:
    def test_flips_to_available(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
        in_memory_drive: InMemoryDriveClient,
        db_session: Any,
    ) -> None:
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
        )
        save_refresh_token(str(user_fixture.keycloak_uuid), "refresh-token")
        in_progress_deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.IN_PROGRESS,
        )

        response = deliverables_client.post(
            f"/{in_progress_deliverable.id}/success",
            json={"report_response": _decision_record_body()},
        )

        assert response.status_code == 200
        db_session.refresh(in_progress_deliverable)
        db_session.refresh(meeting)
        assert in_progress_deliverable.status == DeliverableStatus.AVAILABLE
        assert in_progress_deliverable.external_url == in_memory_drive.url
        assert meeting.status == MeetingStatus.TRANSCRIPTION_DONE
        assert len(in_memory_s3.objects) == 1
        assert len(in_memory_email.sent) == 1

    def test_409_when_still_pending(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
        in_memory_drive: InMemoryDriveClient,
        db_session: Any,
    ) -> None:
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
        )
        pending_deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.PENDING,
        )

        response = deliverables_client.post(
            f"/{pending_deliverable.id}/success",
            json={"report_response": _decision_record_body()},
        )

        assert response.status_code == 409
        db_session.refresh(pending_deliverable)
        assert pending_deliverable.status == DeliverableStatus.PENDING


class TestFailureCallbackRoute:
    def test_flips_to_failed(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
        db_session: Any,
    ) -> None:
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
        )
        pending_deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.PENDING,
        )

        response = deliverables_client.post(f"/{pending_deliverable.id}/fail")

        assert response.status_code == 200
        db_session.refresh(pending_deliverable)
        db_session.refresh(meeting)
        assert pending_deliverable.status == DeliverableStatus.FAILED
        assert meeting.status == MeetingStatus.TRANSCRIPTION_DONE

    def test_legacy_failure_alias_still_flips_to_failed(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
        db_session: Any,
    ) -> None:
        """Old mcr-generation workers call /failure during a rolling deploy; the
        alias must keep working so the deliverable never strands in PENDING."""
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.REPORT_PENDING,
            name_platform=MeetingPlatforms.COMU,
        )
        pending_deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.PENDING,
        )

        response = deliverables_client.post(f"/{pending_deliverable.id}/failure")

        assert response.status_code == 200
        db_session.refresh(pending_deliverable)
        assert pending_deliverable.status == DeliverableStatus.FAILED


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


class TestGetFileRoute:
    @pytest.mark.parametrize(
        ("deliverable_type", "expected_prefix"),
        [
            (DeliverableType.DECISION_RECORD, "Releve_Decision"),
            (DeliverableType.DETAILED_SYNTHESIS, "Synthese_Detaillee"),
            (DeliverableType.CUSTOM_REPORT, "Compte_Rendu_Personnalise"),
        ],
    )
    def test_streams_typed_docx_from_s3(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
        mocker: Any,
        deliverable_type: DeliverableType,
        expected_prefix: str,
    ) -> None:
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.REPORT_DONE,
            name_platform=MeetingPlatforms.COMU,
            name="My Meeting",
            report_filename="decision_record.docx",
        )
        deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=deliverable_type,
            status=DeliverableStatus.AVAILABLE,
        )
        mocker.patch(
            "mcr_meeting.app.use_cases.get_deliverable_file.get_typed_deliverable_from_s3",
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
        disposition = response.headers["content-disposition"]
        assert disposition.startswith("attachment; filename*=UTF-8''")
        assert f"{expected_prefix}_My%20Meeting.docx" in disposition
        assert response.content == b"typed docx content"

    def test_url_encodes_accented_meeting_name_in_header(
        self,
        deliverables_client: PrefixedTestClient,
        user_fixture: User,
        mocker: Any,
    ) -> None:
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.REPORT_DONE,
            name="Réunion équipe",
        )
        deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=DeliverableType.DECISION_RECORD,
            status=DeliverableStatus.AVAILABLE,
        )
        mocker.patch(
            "mcr_meeting.app.use_cases.get_deliverable_file.get_typed_deliverable_from_s3",
            return_value=BytesIO(b"typed docx content"),
        )

        response = deliverables_client.get(
            f"/{deliverable.id}/file",
            headers={"X-User-Keycloak-UUID": str(user_fixture.keycloak_uuid)},
        )

        assert response.status_code == 200
        assert (
            "Releve_Decision_R%C3%A9union%20%C3%A9quipe.docx"
            in response.headers["content-disposition"]
        )

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
            "mcr_meeting.app.use_cases.get_deliverable_file.get_typed_deliverable_from_s3",
            return_value=None,
        )
        mocker.patch(
            "mcr_meeting.app.use_cases.get_deliverable_file.get_report_from_s3",
            return_value=BytesIO(b"legacy docx content"),
        )

        response = deliverables_client.get(
            f"/{deliverable.id}/file",
            headers={"X-User-Keycloak-UUID": str(user_fixture.keycloak_uuid)},
        )

        assert response.status_code == 200
        assert response.content == b"legacy docx content"
