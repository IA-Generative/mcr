from unittest.mock import Mock

from mcr_meeting.app.models.meeting_model import MeetingPlatforms, MeetingStatus
from mcr_meeting.app.models.user_model import User
from mcr_meeting.app.schemas.report_generation import ReportType
from tests.api.conftest import PrefixedTestClient
from tests.factories import MeetingFactory


class TestGenerateMeetingReport:
    def test_happy_path_single_report_type(
        self,
        meeting_client: PrefixedTestClient,
        user_fixture: User,
        mock_celery_producer_app: Mock,
    ) -> None:
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )

        response = meeting_client.post(
            f"/{meeting.id}/report",
            json={"report_types": ["DECISION_RECORD"]},
            headers={"X-User-Keycloak-UUID": str(user_fixture.keycloak_uuid)},
        )

        assert response.status_code == 200

        mock_celery_producer_app.send_task.assert_called_once()
        call_args = mock_celery_producer_app.send_task.call_args
        assert call_args.kwargs["args"][2] == ReportType.DECISION_RECORD

    def test_empty_list_triggers_validation_error(
        self,
        meeting_client: PrefixedTestClient,
        user_fixture: User,
    ) -> None:
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )

        response = meeting_client.post(
            f"/{meeting.id}/report",
            json={"report_types": []},
            headers={"X-User-Keycloak-UUID": str(user_fixture.keycloak_uuid)},
        )

        assert response.status_code == 422

    def test_invalid_enum_triggers_validation_error(
        self,
        meeting_client: PrefixedTestClient,
        user_fixture: User,
    ) -> None:
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )

        response = meeting_client.post(
            f"/{meeting.id}/report",
            json={"report_types": ["INVALID_TYPE"]},
            headers={"X-User-Keycloak-UUID": str(user_fixture.keycloak_uuid)},
        )

        assert response.status_code == 422

    def test_more_than_one_element_triggers_validation_error(
        self,
        meeting_client: PrefixedTestClient,
        user_fixture: User,
    ) -> None:
        meeting = MeetingFactory.create(
            owner=user_fixture,
            status=MeetingStatus.TRANSCRIPTION_DONE,
            name_platform=MeetingPlatforms.COMU,
            transcription_filename="transcription.docx",
        )

        response = meeting_client.post(
            f"/{meeting.id}/report",
            json={"report_types": ["DECISION_RECORD", "DETAILED_SYNTHESIS"]},
            headers={"X-User-Keycloak-UUID": str(user_fixture.keycloak_uuid)},
        )

        assert response.status_code == 422
