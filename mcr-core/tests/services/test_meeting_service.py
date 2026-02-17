"""
Unit tests for the create_meeting_service function.
Focus on transaction rollback, error handling, and service-layer logic.
"""

from datetime import datetime, timezone

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from mcr_meeting.app.exceptions.exceptions import NotSavedException
from mcr_meeting.app.models import Meeting, MeetingPlatforms, MeetingStatus, User
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.schemas.meeting_schema import MeetingCreate
from mcr_meeting.app.services.meeting_service import create_meeting_service
from tests.factories.user_factory import UserFactory


@pytest.fixture
def user_fixture() -> User:
    user = UserFactory.create()
    return user


class TestCreateMeetingService:
    """Test suite for the create_meeting_service function."""

    def test_create_meeting_service_success_with_minimal_fields(
        self, db_session: Session, user_fixture: User
    ) -> None:
        """Test successful meeting creation with only required fields."""
        # Arrange
        meeting_data = MeetingCreate(
            name="Test Meeting",
            name_platform=MeetingPlatforms.COMU,
            creation_date=datetime(2024, 10, 1, 12, 0, tzinfo=timezone.utc),
            url="https://webconf.comu.gouv.fr/meeting/123456?secret=GF2e74BjOcDR1Bq6nvv5wA",
        )

        # Act
        result = create_meeting_service(meeting_data, user_fixture.keycloak_uuid)

        # Assert
        assert result.id is not None
        assert result.name == "Test Meeting"
        assert result.name_platform == MeetingPlatforms.COMU
        assert result.user_id == user_fixture.id
        assert result.status == MeetingStatus.NONE

        # Verify meeting was actually persisted to database
        db_meeting = db_session.get(Meeting, result.id)
        assert db_meeting is not None
        assert db_meeting.name == "Test Meeting"

    def test_create_meeting_service_success_with_all_fields(
        self, db_session: Session, user_fixture: User
    ) -> None:
        """Test successful meeting creation with all optional fields populated."""
        # Arrange
        meeting_data = MeetingCreate(
            name="Comprehensive Meeting",
            name_platform=MeetingPlatforms.COMU,
            creation_date=datetime(2024, 10, 1, 12, 0, tzinfo=timezone.utc),
            url="https://webconf.comu.gouv.fr/meeting/123456?secret=GF2e74BjOcDR1Bq6nvv5wA",
            meeting_password="123456",
            meeting_platform_id="platform-123",
            status=MeetingStatus.NONE,  # Service will override based on platform
        )

        # Act
        result = create_meeting_service(meeting_data, user_fixture.keycloak_uuid)

        # Assert
        assert result.id is not None
        assert result.name == "Comprehensive Meeting"
        assert result.meeting_password == "123456"
        assert result.meeting_platform_id == "platform-123"
        # COMU platform should result in NONE status
        assert result.status == MeetingStatus.NONE
        assert (
            result.url
            == "https://webconf.comu.gouv.fr/meeting/123456?secret=GF2e74BjOcDR1Bq6nvv5wA"
        )

    def test_create_meeting_service_sets_import_pending_for_mcr_import(
        self, db_session: Session, user_fixture: User
    ) -> None:
        """Test that MCR_IMPORT platform sets status to IMPORT_PENDING."""
        # Arrange
        meeting_data = MeetingCreate(
            name="Import Meeting",
            name_platform=MeetingPlatforms.MCR_IMPORT,
            creation_date=datetime(2024, 10, 1, 12, 0, tzinfo=timezone.utc),
        )

        # Act
        result = create_meeting_service(meeting_data, user_fixture.keycloak_uuid)

        # Assert
        assert result.id is not None
        assert result.name_platform == MeetingPlatforms.MCR_IMPORT
        assert result.status == MeetingStatus.IMPORT_PENDING

    def test_create_meeting_service_sets_capture_in_progress_for_mcr_record(
        self, db_session: Session, user_fixture: User
    ) -> None:
        """Test that MCR_RECORD platform sets status to CAPTURE_IN_PROGRESS."""
        # Arrange
        meeting_data = MeetingCreate(
            name="Record Meeting",
            name_platform=MeetingPlatforms.MCR_RECORD,
            creation_date=datetime(2024, 10, 1, 12, 0, tzinfo=timezone.utc),
        )

        # Act
        result = create_meeting_service(meeting_data, user_fixture.keycloak_uuid)

        # Assert
        assert result.id is not None
        assert result.name_platform == MeetingPlatforms.MCR_RECORD
        assert result.status == MeetingStatus.CAPTURE_IN_PROGRESS

    def test_create_meeting_service_sets_none_for_visio(
        self, db_session: Session, user_fixture: User
    ) -> None:
        """Test that VISIO platform sets status to NONE."""
        # Arrange
        meeting_data = MeetingCreate(
            name="Visio Meeting",
            name_platform=MeetingPlatforms.VISIO,
            creation_date=datetime(2024, 10, 1, 12, 0, tzinfo=timezone.utc),
            url="https://visio.numerique.gouv.fr/aaa-bbbb-ccc",
        )

        # Act
        result = create_meeting_service(meeting_data, user_fixture.keycloak_uuid)

        # Assert
        assert result.id is not None
        assert result.name_platform == MeetingPlatforms.VISIO
        assert result.status == MeetingStatus.NONE

        # Verify meeting was actually persisted to database
        db_meeting = db_session.get(Meeting, result.id)
        assert db_meeting is not None
        assert db_meeting.name == "Visio Meeting"

    def test_create_meeting_service_sets_none_for_other_platforms(
        self, db_session: Session, user_fixture: User
    ) -> None:
        """Test that other platforms (WEBCONF) set status to NONE."""
        # Arrange
        meeting_data = MeetingCreate(
            name="WebConf Meeting",
            name_platform=MeetingPlatforms.WEBCONF,
            creation_date=datetime(2024, 10, 1, 12, 0, tzinfo=timezone.utc),
            url="https://webconf.numerique.gouv.fr/AbCdEf1234",
        )

        # Act
        result = create_meeting_service(meeting_data, user_fixture.keycloak_uuid)

        # Assert
        assert result.id is not None
        assert result.name_platform == MeetingPlatforms.WEBCONF
        assert result.status == MeetingStatus.NONE

    def test_create_meeting_service_raises_not_saved_exception_on_sqlalchemy_error(
        self, db_session: Session, user_fixture: User, mocker: MockerFixture
    ) -> None:
        """Test that generic SQLAlchemyError is caught and raises NotSavedException."""
        # Arrange
        meeting_data = MeetingCreate(
            name="Test Meeting",
            name_platform=MeetingPlatforms.COMU,
            creation_date=datetime(2024, 10, 1, 12, 0, tzinfo=timezone.utc),
            url="https://webconf.comu.gouv.fr/meeting/123456?secret=GF2e74BjOcDR1Bq6nvv5wA",
        )

        # Mock db.commit() to raise generic SQLAlchemyError
        mock_commit = mocker.patch.object(
            db_session,
            "commit",
            side_effect=SQLAlchemyError("Database connection lost"),
        )

        # Act & Assert
        with pytest.raises(NotSavedException) as exc_info:
            create_meeting_service(meeting_data, user_fixture.keycloak_uuid)

        assert "Erreur lors de la transaction" in str(exc_info.value)
        assert "Database connection lost" in str(exc_info.value)
        mock_commit.assert_called_once()

    def test_create_meeting_service_rollback_on_error_leaves_db_clean(
        self, db_session: Session, user_fixture: User, mocker: MockerFixture
    ) -> None:
        """
        Test that automatic rollback on error leaves database in clean state.
        Verify no partial data persists after a failed transaction.
        """
        # Arrange
        meeting_data = MeetingCreate(
            name="Test Meeting",
            name_platform=MeetingPlatforms.COMU,
            creation_date=datetime(2024, 10, 1, 12, 0, tzinfo=timezone.utc),
            url="https://webconf.comu.gouv.fr/meeting/123456?secret=GF2e74BjOcDR1Bq6nvv5wA",
        )

        # Count meetings before attempt
        initial_count = db_session.query(Meeting).count()

        # Mock commit to fail
        mocker.patch.object(
            db_session,
            "commit",
            side_effect=SQLAlchemyError("Simulated database error"),
        )

        # Act
        with pytest.raises(NotSavedException):
            create_meeting_service(meeting_data, user_fixture.keycloak_uuid)

        # Assert - Database should be in same state as before
        final_count = db_session.query(Meeting).count()
        assert final_count == initial_count, (
            "Database should have no new meetings after rollback"
        )

        # Verify the meeting object is not in the session
        meetings = (
            db_session.query(Meeting).filter(Meeting.name == "Test Meeting").all()
        )
        assert len(meetings) == 0, "No meeting with that name should exist"

    def test_create_meeting_service_session_usable_after_error(
        self, db_session: Session, user_fixture: User, mocker: MockerFixture
    ) -> None:
        """
        Test that session remains healthy and usable after a failed save.
        Verify subsequent operations can succeed.
        """
        # Eagerly load user UUID to prevent detached object issues after rollback
        user_keycloak_uuid = user_fixture.keycloak_uuid

        # Arrange - First meeting will fail
        failing_meeting_data = MeetingCreate(
            name="Failing Meeting",
            name_platform=MeetingPlatforms.COMU,
            creation_date=datetime(2024, 10, 1, 12, 0, tzinfo=timezone.utc),
            url="https://webconf.comu.gouv.fr/meeting/123456?secret=GF2e74BjOcDR1Bq6nvv5wA",
        )

        successful_meeting_data = MeetingCreate(
            name="Successful Meeting",
            name_platform=MeetingPlatforms.COMU,
            creation_date=datetime(2024, 10, 2, 12, 0, tzinfo=timezone.utc),
            url="https://webconf.comu.gouv.fr/meeting/789012?secret=XYZ789abc012DEF345GHI_",
        )

        # Mock commit to fail only once
        original_commit = db_session.commit
        commit_call_count = [0]

        def mock_commit_once() -> None:
            commit_call_count[0] += 1
            if commit_call_count[0] == 1:
                raise SQLAlchemyError("First commit fails")
            return original_commit()

        mocker.patch.object(db_session, "commit", side_effect=mock_commit_once)

        # Act - First save should fail
        with pytest.raises(NotSavedException):
            create_meeting_service(failing_meeting_data, user_keycloak_uuid)

        # Act - Second save should succeed (session should be healthy)
        result = create_meeting_service(successful_meeting_data, user_keycloak_uuid)

        # Assert - Second meeting should be saved successfully
        assert result.id is not None
        assert result.name == "Successful Meeting"

        # Verify only the successful meeting exists
        meetings = db_session.query(Meeting).all()
        assert len(meetings) == 1
        assert meetings[0].name == "Successful Meeting"

    def test_create_meeting_service_rollback_on_commit_failure(
        self, db_session: Session, user_fixture: User, mocker: MockerFixture
    ) -> None:
        """
        Test explicit rollback behavior when commit fails.
        Mock commit failure and verify database state.
        """
        # Arrange
        meeting_data = MeetingCreate(
            name="Commit Failure Meeting",
            name_platform=MeetingPlatforms.COMU,
            creation_date=datetime(2024, 10, 1, 12, 0, tzinfo=timezone.utc),
            url="https://webconf.comu.gouv.fr/meeting/123456?secret=GF2e74BjOcDR1Bq6nvv5wA",
        )

        # Track if meeting was added to session
        original_add = db_session.add
        added_objects = []

        def track_add(obj: object) -> None:
            added_objects.append(obj)
            return original_add(obj)

        mocker.patch.object(db_session, "add", side_effect=track_add)

        # Mock commit to fail
        mocker.patch.object(
            db_session,
            "commit",
            side_effect=SQLAlchemyError("Commit failed"),
        )

        # Act
        with pytest.raises(NotSavedException):
            create_meeting_service(meeting_data, user_fixture.keycloak_uuid)

        # Assert
        assert len(added_objects) == 2, (
            "Meeting and MeetingTransitionRecord should have been added to session"
        )
        assert isinstance(added_objects[0], Meeting)
        assert isinstance(added_objects[1], MeetingTransitionRecord)

        # Verify meeting is NOT in database after rollback
        meeting_count = (
            db_session.query(Meeting)
            .filter(Meeting.name == "Commit Failure Meeting")
            .count()
        )
        assert meeting_count == 0, "Meeting should not exist after rollback"

    def test_create_meeting_service_within_existing_transaction(
        self, db_session: Session, user_fixture: User
    ) -> None:
        """
        Test create_meeting_service behavior when called within an existing transaction.
        Verify nested transaction handling.
        """
        # Arrange
        meeting_data = MeetingCreate(
            name="Nested Transaction Meeting",
            name_platform=MeetingPlatforms.COMU,
            creation_date=datetime(2024, 10, 1, 12, 0, tzinfo=timezone.utc),
            url="https://webconf.comu.gouv.fr/meeting/123456?secret=GF2e74BjOcDR1Bq6nvv5wA",
        )

        # Act - Call create_meeting_service within the test's existing transaction
        # (db_session fixture already has a transaction open)
        result = create_meeting_service(meeting_data, user_fixture.keycloak_uuid)

        # Assert - Meeting should be created successfully
        assert result.id is not None
        assert result.name == "Nested Transaction Meeting"

        # Verify meeting exists in database
        db_meeting = db_session.query(Meeting).filter(Meeting.id == result.id).first()
        assert db_meeting is not None
        assert db_meeting.name == "Nested Transaction Meeting"
