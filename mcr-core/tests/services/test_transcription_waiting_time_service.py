from datetime import datetime, timedelta, timezone

import pytest

from mcr_meeting.app.models.meeting_model import MeetingStatus
from mcr_meeting.app.services.transcription_waiting_time_service import (
    TranscriptionQueueEstimationService,
)
from tests.factories import MeetingFactory, MeetingTransitionRecordFactory


class TestTranscriptionQueueEstimationService:
    """Tests for the transcription queue estimation service."""

    def test_estimate_wait_time_should_return_zero_when_no_pending_meetings(
        self,
    ) -> None:
        """Test that wait time is 0 when there are no pending meetings."""
        # Arrange - no meetings created, so count is 0

        # Act
        result = (
            TranscriptionQueueEstimationService.estimate_current_wait_time_minutes()
        )

        # Assert
        # 0 slots * 12 minutes = 0 minutes
        assert result == 0

    def test_estimate_wait_time_should_return_zero_when_slot_are_not_fully_filled(
        self,
    ) -> None:
        """Test calculation for meetings that fit in one slot (< 14 meetings)."""
        # Arrange - create 5 pending meetings
        MeetingFactory.create_batch(5, status=MeetingStatus.TRANSCRIPTION_PENDING)

        # Act
        result = (
            TranscriptionQueueEstimationService.estimate_current_wait_time_minutes()
        )

        # Assert
        # 5 meetings / 14 parallel pods = 0 slots needed (floor division)
        # 0 slots * 12 minutes = 0 minutes
        expected_wait_time = 0
        assert result == expected_wait_time

    def test_calculate_wait_time_from_count_should_calculate_correctly_for_exact_multiple(
        self,
    ) -> None:
        """Test calculation for an exact multiple of parallel pods count."""
        # Arrange - create 28 pending meetings (2 * 14)
        MeetingFactory.create_batch(28, status=MeetingStatus.TRANSCRIPTION_PENDING)

        # Act
        result = (
            TranscriptionQueueEstimationService.estimate_current_wait_time_minutes()
        )

        # Assert
        # 28 meetings / 14 parallel pods = 2 slots needed
        # 2 slots * 12 minutes = 24 minutes
        expected_wait_time = 24
        assert result == expected_wait_time

    def test_calculate_wait_time_from_count_should_add_extra_slot_for_remainder(
        self,
    ) -> None:
        """Test that calculation uses floor division (no extra slot for remainder)."""
        # Arrange - create 15 pending meetings (1 * 14 + 1)
        MeetingFactory.create_batch(15, status=MeetingStatus.TRANSCRIPTION_PENDING)

        # Act
        result = (
            TranscriptionQueueEstimationService.estimate_current_wait_time_minutes()
        )

        # Assert
        # 15 meetings / 14 parallel pods = 1 slot needed (floor division)
        # 1 slot * 12 minutes = 12 minutes
        expected_wait_time = 12
        assert result == expected_wait_time

    def test_calculate_wait_time_from_count_should_handle_large_numbers(self) -> None:
        """Test calculation with a large number of pending meetings."""
        # Arrange - create 100 pending meetings
        nb_meeting_pending = 100
        MeetingFactory.create_batch(
            nb_meeting_pending, status=MeetingStatus.TRANSCRIPTION_PENDING
        )

        # Act
        result = (
            TranscriptionQueueEstimationService.estimate_current_wait_time_minutes()
        )

        # Assert
        # 100 meetings / 14 parallel pods = 7 slots (floor division)
        # 7 slots * 12 minutes = 84 minutes
        expected_wait_time = nb_meeting_pending // 14 * 12
        assert result == expected_wait_time

    def test_get_meeting_transcription_wait_time_minutes_should_calculate_correctly_with_pending_meetings(
        self,
    ) -> None:
        """Test correct calculation when there are pending meetings."""
        # Arrange - create 20 pending meetings
        pending_count = 20
        MeetingFactory.create_batch(
            pending_count, status=MeetingStatus.TRANSCRIPTION_PENDING
        )

        # Act
        result = (
            TranscriptionQueueEstimationService.estimate_current_wait_time_minutes()
        )

        # Assert
        # 20 meetings / 14 parallel pods = 1 slot (floor division)
        # 1 slot * 12 minutes = 12 minutes
        expected_wait_time = pending_count // 14 * 12
        assert result == expected_wait_time

    def test_get_meeting_transcription_wait_time_minutes_should_not_be_impacted_by_other_meetings(
        self,
    ) -> None:
        """Test that count_pending_meetings only counts meetings with TRANSCRIPTION_PENDING status."""
        # Arrange
        MeetingFactory.create_batch(
            13,
            status=MeetingStatus.TRANSCRIPTION_PENDING,
        )  # Should count
        MeetingFactory.create_batch(
            2,
            status=MeetingStatus.TRANSCRIPTION_DONE,
        )  # Should NOT count (wrong status)
        MeetingFactory.create_batch(
            2,
            status=MeetingStatus.CAPTURE_IN_PROGRESS,
        )  # Should NOT count (wrong status)

        # Act
        result = (
            TranscriptionQueueEstimationService.estimate_current_wait_time_minutes()
        )

        # Assert
        # Should count only 13 meetings (only meetings with TRANSCRIPTION_PENDING status)
        # So a slot is still free => wait_time is 0
        assert result == 0

    def test_get_meeting_remaining_wait_time_minutes_should_return_correct_remaining_time(
        self,
    ) -> None:
        """Test that get_meeting_remaining_wait_time_minutes returns correct remaining time."""
        # Arrange - create meeting with transition record predicting 30 minutes in future
        meeting = MeetingFactory.create(status=MeetingStatus.TRANSCRIPTION_IN_PROGRESS)
        predicted_time = datetime.now(timezone.utc) + timedelta(minutes=30)

        MeetingTransitionRecordFactory.create(
            meeting_id=meeting.id,
            status=MeetingStatus.TRANSCRIPTION_IN_PROGRESS,
            predicted_date_of_next_transition=predicted_time,
        )

        # Act
        result = (
            TranscriptionQueueEstimationService.get_meeting_remaining_wait_time_minutes(
                meeting.id
            )
        )

        # Assert - should be approximately 30 minutes (within 1 minute for test execution)
        assert 29 <= result <= 31

    def test_get_meeting_remaining_wait_time_minutes_should_return_zero_when_time_passed(
        self,
    ) -> None:
        """Test that get_meeting_remaining_wait_time_minutes returns 0 when estimated time has passed."""
        # Arrange - create meeting with transition record in the past
        meeting = MeetingFactory.create(status=MeetingStatus.TRANSCRIPTION_IN_PROGRESS)
        past_time = datetime.now(timezone.utc) - timedelta(minutes=10)

        MeetingTransitionRecordFactory.create(
            meeting_id=meeting.id,
            status=MeetingStatus.TRANSCRIPTION_IN_PROGRESS,
            predicted_date_of_next_transition=past_time,
        )

        # Act
        result = (
            TranscriptionQueueEstimationService.get_meeting_remaining_wait_time_minutes(
                meeting.id
            )
        )

        # Assert
        assert result == 0

    def test_get_meeting_remaining_wait_time_minutes_should_raise_exception_when_predicted_date_of_next_transition_is_none(
        self,
    ) -> None:
        """Test that get_meeting_remaining_wait_time_minutes raises ValueError when predicted_date_of_next_transition is None."""
        # Arrange - create meeting with transition record that has no prediction
        meeting = MeetingFactory.create(status=MeetingStatus.TRANSCRIPTION_IN_PROGRESS)

        MeetingTransitionRecordFactory.create(
            meeting_id=meeting.id,
            status=MeetingStatus.TRANSCRIPTION_IN_PROGRESS,
            predicted_date_of_next_transition=None,
        )

        # Act & Assert
        with pytest.raises(
            ValueError, match=f"Estimated end date is None for meeting {meeting.id}"
        ):
            TranscriptionQueueEstimationService.get_meeting_remaining_wait_time_minutes(
                meeting.id
            )
