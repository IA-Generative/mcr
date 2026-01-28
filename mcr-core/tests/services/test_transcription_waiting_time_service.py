from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from mcr_meeting.app.exceptions.exceptions import NotFoundException
from mcr_meeting.app.services.transcription_waiting_time_service import (
    TranscriptionQueueEstimationService,
)


class TestTranscriptionQueueEstimationService:
    """Tests for the transcription queue estimation service."""

    def test_calculate_wait_time_from_count_should_return_base_duration_when_no_pending_meetings(
        self, mocker: MockerFixture
    ) -> None:
        """Test that wait time is base duration when there are no pending meetings."""
        # Arrange
        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.count_pending_meetings",
            return_value=0,
        )

        # Act
        result = (
            TranscriptionQueueEstimationService.estimate_current_wait_time_minutes()
        )

        # Assert
        # 0 slots * 12 minutes + 60 minutes (base meeting duration) = 60 minutes
        assert result == 60

    def test_calculate_wait_time_from_count_should_calculate_correctly_for_one_slot(
        self, mocker: MockerFixture
    ) -> None:
        """Test calculation for meetings that fit in one slot (< 14 meetings)."""
        # Arrange
        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.count_pending_meetings",
            return_value=5,
        )

        # Act
        result = (
            TranscriptionQueueEstimationService.estimate_current_wait_time_minutes()
        )

        # Assert
        expected_wait_time = (
            60  # 0 slots * 12 minutes + 60 minutes (base meeting duration)
        )
        assert result == expected_wait_time

    def test_calculate_wait_time_from_count_should_calculate_correctly_for_exact_multiple(
        self, mocker: MockerFixture
    ) -> None:
        """Test calculation for an exact multiple of parallel pods count."""
        # Arrange
        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.count_pending_meetings",
            return_value=28,  # 2 * 14
        )

        # Act
        result = (
            TranscriptionQueueEstimationService.estimate_current_wait_time_minutes()
        )

        # Assert
        expected_wait_time = (
            84  # 2 slots * 12 minutes + 60 minutes (base meeting duration)
        )
        assert result == expected_wait_time

    def test_calculate_wait_time_from_count_should_add_extra_slot_for_remainder(
        self, mocker: MockerFixture
    ) -> None:
        """Test that calculation adds an extra slot when there's a remainder."""
        # Arrange
        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.count_pending_meetings",
            return_value=15,  # 1 * 14 + 1
        )

        # Act
        result = (
            TranscriptionQueueEstimationService.estimate_current_wait_time_minutes()
        )

        # Assert
        expected_wait_time = (
            72  # 1 slot * 12 minutes + 60 minutes (base meeting duration)
        )
        assert result == expected_wait_time

    def test_calculate_wait_time_from_count_should_handle_large_numbers(
        self, mocker: MockerFixture
    ) -> None:
        """Test calculation with a large number of pending meetings."""
        # Arrange
        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.count_pending_meetings",
            return_value=100,
        )

        # Act
        result = (
            TranscriptionQueueEstimationService.estimate_current_wait_time_minutes()
        )

        # Assert
        # 100 / 14 = 7.14, so we need 7 slots
        expected_wait_time = 144  # 7 slots * 12 minutes + 60 minutes (base meeting duration) = 144 minutes
        assert result == expected_wait_time

    def test_get_meeting_transcription_wait_time_minutes_should_calculate_correctly_with_pending_meetings(
        self, mocker: MockerFixture
    ) -> None:
        """Test correct calculation when there are pending meetings."""
        # Arrange

        pending_count = 20
        expected_wait_time = (
            72  # 1 slot * 12 minutes + 60 minutes (base meeting duration) = 72 minutes
        )
        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.count_pending_meetings",
            return_value=pending_count,
        )

        # Act
        result = (
            TranscriptionQueueEstimationService.estimate_current_wait_time_minutes()
        )

        # Assert
        assert result == expected_wait_time

    def test_get_meeting_remaining_wait_time_minutes_should_return_correct_remaining_time(
        self, mocker: MockerFixture
    ) -> None:
        """Test that get_meeting_remaining_wait_time_minutes returns correct remaining time."""
        # Arrange
        meeting_id = 1

        mock_transition_record = Mock()
        fixed_time = datetime(2024, 10, 1, 12, 0, tzinfo=timezone.utc)
        mock_transition_record.predicted_date_of_next_transition = (
            fixed_time + timedelta(minutes=30)
        )

        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.find_transition_record_by_meeting_and_status",
            return_value=mock_transition_record,
        )
        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.datetime",
            wraps=datetime,
        )
        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.datetime.now",
            return_value=fixed_time,
        )

        # Act
        result = (
            TranscriptionQueueEstimationService.get_meeting_remaining_wait_time_minutes(
                meeting_id
            )
        )

        # Assert
        assert result == 30

    def test_get_meeting_remaining_wait_time_minutes_should_return_zero_when_time_passed(
        self, mocker: MockerFixture
    ) -> None:
        """Test that get_meeting_remaining_wait_time_minutes returns 0 when estimated time has passed."""
        # Arrange
        meeting_id = 1

        mock_transition_record = Mock()
        mock_transition_record.predicted_date_of_next_transition = datetime.now(
            timezone.utc
        ) - timedelta(minutes=10)

        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.find_transition_record_by_meeting_and_status",
            return_value=mock_transition_record,
        )

        # Act
        result = (
            TranscriptionQueueEstimationService.get_meeting_remaining_wait_time_minutes(
                meeting_id
            )
        )

        # Assert
        assert result == 0

    def test_get_meeting_remaining_wait_time_minutes_should_raise_exception_when_transition_record_not_found(
        self, mocker: MockerFixture
    ) -> None:
        """Test that get_meeting_remaining_wait_time_minutes raises ValueError when transition record not found."""
        # Arrange
        meeting_id = 1
        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.find_transition_record_by_meeting_and_status",
            return_value=None,
        )

        # Act & Assert
        with pytest.raises(
            NotFoundException, match="Meeting transition record with ID 1 not found"
        ):
            TranscriptionQueueEstimationService.get_meeting_remaining_wait_time_minutes(
                meeting_id
            )

    def test_get_meeting_remaining_wait_time_minutes_should_raise_exception_when_predicted_date_of_next_transition_is_none(
        self, mocker: MockerFixture
    ) -> None:
        """Test that get_meeting_remaining_wait_time_minutes raises ValueError when predicted_date_of_next_transition is None."""
        # Arrange
        meeting_id = 1
        mock_transition_record = Mock()
        mock_transition_record.predicted_date_of_next_transition = None

        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.find_transition_record_by_meeting_and_status",
            return_value=mock_transition_record,
        )

        # Act & Assert
        with pytest.raises(
            ValueError, match="Estimated end date is None for meeting 1"
        ):
            TranscriptionQueueEstimationService.get_meeting_remaining_wait_time_minutes(
                meeting_id
            )
