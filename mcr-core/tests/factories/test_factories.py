from mcr_meeting.app.models.meeting_model import MeetingPlatforms, MeetingStatus
from mcr_meeting.app.models.user_model import Role
from tests.factories import (
    MeetingFactory,
    MeetingTransitionRecordFactory,
    TranscriptionFactory,
    UserFactory,
)


class TestUserFactory:
    """Test UserFactory."""

    def test_create_user(self) -> None:
        """Test basic user creation."""
        user = UserFactory.create()

        assert user.id is not None
        assert user.first_name is not None
        assert user.last_name is not None
        assert user.email is not None
        assert user.keycloak_uuid is not None
        assert user.role == Role.USER

    def test_admin_trait(self) -> None:
        """Test admin trait."""
        admin = UserFactory.create(admin=True)

        assert admin.role == Role.ADMIN
        assert admin.entity_name == "Admin Team"

    def test_override_fields(self) -> None:
        """Test overriding factory fields."""
        user = UserFactory.create(
            first_name="Wade",
            last_name="Wilson",
            email="wade.wilson@fake.com",
        )

        assert user.first_name == "Wade"
        assert user.last_name == "Wilson"
        assert user.email == "wade.wilson@fake.com"

    def test_unique_emails(self) -> None:
        """Test that multiple users get unique emails."""
        user1 = UserFactory.create()
        user2 = UserFactory.create()

        assert user1.email != user2.email

    def test_unique_uuids(self) -> None:
        """Test that multiple users get unique UUIDs."""
        user1 = UserFactory.create()
        user2 = UserFactory.create()

        assert user1.keycloak_uuid != user2.keycloak_uuid

    def test_batch_creation(self) -> None:
        """Test batch creation of users."""
        users = UserFactory.create_batch(5)

        assert len(users) == 5
        assert all(user.id is not None for user in users)
        # Check all emails are unique
        emails = [user.email for user in users]
        assert len(emails) == len(set(emails))


class TestMeetingFactory:
    """Test MeetingFactory."""

    def test_create_meeting(self) -> None:
        """Test basic meeting creation."""
        meeting = MeetingFactory.create()

        assert meeting.id is not None
        assert meeting.name is not None
        assert meeting.name_platform == MeetingPlatforms.COMU
        assert meeting.status == MeetingStatus.NONE
        assert meeting.owner is not None
        assert meeting.user_id == meeting.owner.id

    def test_import_meeting_trait(self) -> None:
        """Test import_meeting trait."""
        meeting = MeetingFactory.create(import_meeting=True)

        assert meeting.name_platform == MeetingPlatforms.MCR_IMPORT
        assert meeting.url is None
        assert meeting.meeting_platform_id is None

    def test_record_meeting_trait(self) -> None:
        """Test record_meeting trait."""
        meeting = MeetingFactory.create(record_meeting=True)

        assert meeting.name_platform == MeetingPlatforms.MCR_RECORD
        assert meeting.url is None
        assert meeting.meeting_platform_id is None

    def test_with_dates_trait(self) -> None:
        """Test with_dates trait."""
        meeting = MeetingFactory.create(with_dates=True)

        assert meeting.start_date is not None
        assert meeting.end_date is not None
        assert meeting.end_date > meeting.start_date

    def test_with_transcription_trait(self) -> None:
        """Test with_transcription trait."""
        meeting = MeetingFactory.create(with_transcription=True)

        assert meeting.transcription_filename == "transcription_file.json"
        assert meeting.status == MeetingStatus.TRANSCRIPTION_DONE

    def test_with_report_trait(self) -> None:
        """Test with_report trait."""
        meeting = MeetingFactory.create(with_report=True)

        assert meeting.report_filename == "report_file.json"
        assert meeting.status == MeetingStatus.REPORT_DONE

    def test_use_specific_owner(self) -> None:
        """Test using a specific owner."""
        user = UserFactory.create(first_name="John", last_name="Doe")
        meeting = MeetingFactory.create(owner=user)

        assert meeting.owner.id == user.id
        assert meeting.user_id == user.id
        assert meeting.owner.first_name == "John"

    def test_override_fields(self) -> None:
        """Test overriding factory fields."""
        meeting = MeetingFactory.create(
            name="Specific Meeting",
            status=MeetingStatus.CAPTURE_DONE,
        )

        assert meeting.name == "Specific Meeting"
        assert meeting.status == MeetingStatus.CAPTURE_DONE

    def test_batch_creation(self) -> None:
        """Test batch creation of meetings."""
        meetings = MeetingFactory.create_batch(3)

        assert len(meetings) == 3
        assert all(meeting.id is not None for meeting in meetings)
        # Each should have a different owner
        owner_ids = [meeting.owner.id for meeting in meetings]
        assert len(owner_ids) == len(set(owner_ids))


class TestTranscriptionFactory:
    """Test TranscriptionFactory."""

    def test_create_transcription(self) -> None:
        """Test basic transcription creation."""
        transcription = TranscriptionFactory.create()

        assert transcription.id is not None
        assert transcription.transcription_index is not None
        assert transcription.speaker is not None
        assert transcription.transcription is not None
        assert transcription.meeting is not None
        assert transcription.meeting_id == transcription.meeting.id

    def test_short_text_trait(self) -> None:
        """Test short_text trait."""
        transcription = TranscriptionFactory.create(short_text=True)

        # Short text should be shorter than default paragraph
        assert len(transcription.transcription.split()) < 50

    def test_long_text_trait(self) -> None:
        """Test long_text trait."""
        transcription = TranscriptionFactory.create(long_text=True)

        # Long text should be longer than default paragraph
        assert len(transcription.transcription.split()) > 50

    def test_use_specific_meeting(self) -> None:
        """Test using a specific meeting."""
        meeting = MeetingFactory.create(name="Specific Meeting")
        transcription = TranscriptionFactory.create(meeting=meeting)

        assert transcription.meeting.id == meeting.id
        assert transcription.meeting_id == meeting.id
        assert transcription.meeting.name == "Specific Meeting"

    def test_sequential_indices(self) -> None:
        """Test that transcription indices increment sequentially."""
        meeting = MeetingFactory.create()
        transcriptions = TranscriptionFactory.create_batch(5, meeting=meeting)

        indices = [t.transcription_index for t in transcriptions]
        # Indices should be sequential
        assert indices == sorted(indices)
        # Check they're incrementing
        for i in range(1, len(indices)):
            assert indices[i] > indices[i - 1]

    def test_batch_creation_same_meeting(self) -> None:
        """Test batch creation with same meeting."""
        meeting = MeetingFactory.create()
        transcriptions = TranscriptionFactory.create_batch(3, meeting=meeting)

        assert len(transcriptions) == 3
        assert all(t.meeting_id == meeting.id for t in transcriptions)


class TestMeetingTransitionRecordFactory:
    """Test MeetingTransitionRecordFactory."""

    def test_create_transition_record(self) -> None:
        """Test basic transition record creation."""
        record = MeetingTransitionRecordFactory.create()

        assert record.id is not None
        assert record.timestamp is not None
        assert record.status == MeetingStatus.NONE
        assert record.meeting_id is not None

    def test_with_prediction_trait(self) -> None:
        """Test with_prediction trait."""
        record = MeetingTransitionRecordFactory.create(with_prediction=True)

        assert record.predicted_date_of_next_transition is not None
        assert record.predicted_date_of_next_transition > record.timestamp

    def test_transcription_pending_trait(self) -> None:
        """Test transcription_pending trait."""
        record = MeetingTransitionRecordFactory.create(transcription_pending=True)

        assert record.status == MeetingStatus.TRANSCRIPTION_PENDING
        assert record.predicted_date_of_next_transition is not None

    def test_transcription_in_progress_trait(self) -> None:
        """Test transcription_in_progress trait."""
        record = MeetingTransitionRecordFactory.create(transcription_in_progress=True)

        assert record.status == MeetingStatus.TRANSCRIPTION_IN_PROGRESS
        assert record.predicted_date_of_next_transition is not None

    def test_use_specific_meeting(self) -> None:
        """Test using a specific meeting."""
        meeting = MeetingFactory.create(name="Specific Meeting")
        record = MeetingTransitionRecordFactory.create(meeting_id=meeting.id)

        assert record.meeting_id == meeting.id

    def test_batch_creation_same_meeting(self) -> None:
        """Test batch creation with same meeting."""
        meeting = MeetingFactory.create()
        records = MeetingTransitionRecordFactory.create_batch(3, meeting_id=meeting.id)

        assert len(records) == 3
        assert all(r.meeting_id == meeting.id for r in records)
