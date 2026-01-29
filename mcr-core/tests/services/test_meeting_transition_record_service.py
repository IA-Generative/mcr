from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from mcr_meeting.app.db.meeting_repository import (
    count_pending_meetings,
)
from mcr_meeting.app.models.meeting_model import Meeting, MeetingStatus
from mcr_meeting.app.services.meeting_transition_record_service import (
    create_transcription_transition_record_with_estimation,
)


class TestMeetingTransitionRecordService:
    """Tests for the meeting transition record repository."""

    def test_save_meeting_transition_record_should_save_successfully(
        self, meeting_fixture: Meeting
    ) -> None:
        """Test that a transition record is saved successfully."""
        # Act
        result = create_transcription_transition_record_with_estimation(
            meeting_id=meeting_fixture.id,
            meeting_status=MeetingStatus.TRANSCRIPTION_PENDING,
            waiting_time_minutes=24,
        )

        # Assert
        assert result.id is not None
        assert result.meeting_id == meeting_fixture.id
        assert result.status == MeetingStatus.TRANSCRIPTION_PENDING

    def test_count_pending_meetings_should_count_correctly(
        self, db_session: Session
    ) -> None:
        """Test counting pending meetings."""
        # Arrange
        base_date = datetime(2024, 10, 1, 12, 0, tzinfo=timezone.utc)

        # Create meetings with different statuses
        meetings_data = [
            (
                base_date - timedelta(hours=3),
                MeetingStatus.TRANSCRIPTION_PENDING,
            ),  # Should count
            (
                base_date - timedelta(hours=2),
                MeetingStatus.TRANSCRIPTION_PENDING,
            ),  # Should count
            (
                base_date - timedelta(hours=1),
                MeetingStatus.TRANSCRIPTION_DONE,
            ),  # Should NOT count (wrong status)
            (
                base_date + timedelta(hours=1),
                MeetingStatus.CAPTURE_IN_PROGRESS,
            ),  # Should NOT count (wrong status)
        ]

        for creation_date, meeting_status in meetings_data:
            meeting = Meeting(
                user_id=1,
                name=f"Meeting {creation_date}",
                status=meeting_status,
                name_platform="COMU",
                creation_date=creation_date,
            )
            db_session.add(meeting)

        db_session.commit()

        # Act
        count = count_pending_meetings()

        # Assert
        # Should count 2 (only meetings with TRANSCRIPTION_PENDING status)
        assert count == 2

    def test_count_pending_meetings_should_return_zero_when_no_matches(
        self, db_session: Session
    ) -> None:
        """Test that count returns 0 when there are no matching meetings."""
        # Arrange
        # No meetings created

        # Act
        count = count_pending_meetings()

        # Assert
        assert count == 0
