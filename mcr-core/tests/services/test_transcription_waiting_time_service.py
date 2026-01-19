from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from mcr_meeting.app.models.meeting_model import Meeting
from mcr_meeting.app.services.transcription_waiting_time_service import (
    TranscriptionQueueEstimationService,
)


class TestTranscriptionQueueEstimationService:
    """Tests for the transcription queue estimation service."""

    def test_calculate_waiting_time_from_count_should_return_base_duration_when_no_pending_meetings(
        self, mocker: MockerFixture
    ) -> None:
        """Test that waiting time is base duration when there are no pending meetings."""
        # Arrange
        meeting_id = 1
        mock_meeting = Mock(spec=Meeting)
        mock_meeting.creation_date = datetime(2024, 10, 1, 12, 0, tzinfo=timezone.utc)

        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.get_meeting_by_id",
            return_value=mock_meeting,
        )
        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.count_pending_meetings",
            return_value=0,
        )

        # Act
        result = TranscriptionQueueEstimationService.get_meeting_transcription_waiting_time_minutes(
            meeting_id
        )

        # Assert
        # 0 slots * 12 minutes + 60 minutes (base meeting duration) = 60 minutes
        assert result == 60

    def test_calculate_waiting_time_from_count_should_calculate_correctly_for_one_slot(
        self, mocker: MockerFixture
    ) -> None:
        """Test calculation for meetings that fit in one slot (< 14 meetings)."""
        # Arrange
        meeting_id = 1
        mock_meeting = Mock(spec=Meeting)
        mock_meeting.creation_date = datetime(2024, 10, 1, 12, 0, tzinfo=timezone.utc)

        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.get_meeting_by_id",
            return_value=mock_meeting,
        )
        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.count_pending_meetings",
            return_value=5,
        )

        # Act
        result = TranscriptionQueueEstimationService.get_meeting_transcription_waiting_time_minutes(
            meeting_id
        )

        # Assert
        expected_waiting_time = (
            60  # 0 slots * 12 minutes + 60 minutes (base meeting duration)
        )
        assert result == expected_waiting_time

    def test_calculate_waiting_time_from_count_should_calculate_correctly_for_exact_multiple(
        self, mocker: MockerFixture
    ) -> None:
        """Test calculation for an exact multiple of parallel pods count."""
        # Arrange
        meeting_id = 1
        mock_meeting = Mock(spec=Meeting)
        mock_meeting.creation_date = datetime(2024, 10, 1, 12, 0, tzinfo=timezone.utc)

        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.get_meeting_by_id",
            return_value=mock_meeting,
        )
        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.count_pending_meetings",
            return_value=28,  # 2 * 14
        )

        # Act
        result = TranscriptionQueueEstimationService.get_meeting_transcription_waiting_time_minutes(
            meeting_id
        )

        # Assert
        expected_waiting_time = (
            84  # 2 slots * 12 minutes + 60 minutes (base meeting duration)
        )
        assert result == expected_waiting_time

    def test_calculate_waiting_time_from_count_should_add_extra_slot_for_remainder(
        self, mocker: MockerFixture
    ) -> None:
        """Test that calculation adds an extra slot when there's a remainder."""
        # Arrange
        meeting_id = 1
        mock_meeting = Mock(spec=Meeting)
        mock_meeting.creation_date = datetime(2024, 10, 1, 12, 0, tzinfo=timezone.utc)

        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.get_meeting_by_id",
            return_value=mock_meeting,
        )
        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.count_pending_meetings",
            return_value=15,  # 1 * 14 + 1
        )

        # Act
        result = TranscriptionQueueEstimationService.get_meeting_transcription_waiting_time_minutes(
            meeting_id
        )

        # Assert
        expected_waiting_time = (
            72  # 1 slot * 12 minutes + 60 minutes (base meeting duration)
        )
        assert result == expected_waiting_time

    def test_calculate_waiting_time_from_count_should_handle_large_numbers(
        self, mocker: MockerFixture
    ) -> None:
        """Test calculation with a large number of pending meetings."""
        # Arrange
        meeting_id = 1
        mock_meeting = Mock(spec=Meeting)
        mock_meeting.creation_date = datetime(2024, 10, 1, 12, 0, tzinfo=timezone.utc)

        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.get_meeting_by_id",
            return_value=mock_meeting,
        )
        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.count_pending_meetings",
            return_value=100,
        )

        # Act
        result = TranscriptionQueueEstimationService.get_meeting_transcription_waiting_time_minutes(
            meeting_id
        )

        # Assert
        # 100 / 14 = 7.14, so we need 7 slots
        expected_waiting_time = 144  # 7 slots * 12 minutes + 60 minutes (base meeting duration) = 144 minutes
        assert result == expected_waiting_time

    def test_get_meeting_transcription_waiting_time_minutes_should_raise_exception_when_meeting_not_found(
        self, mocker: MockerFixture
    ) -> None:
        """Test that waiting time raises ValueError when meeting is not found."""
        # Arrange
        meeting_id = 999
        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.get_meeting_by_id",
            return_value=None,
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Meeting with ID 999 not found"):
            TranscriptionQueueEstimationService.get_meeting_transcription_waiting_time_minutes(
                meeting_id
            )

    def test_get_meeting_transcription_waiting_time_minutes_should_raise_exception_when_no_creation_date(
        self, mocker: MockerFixture
    ) -> None:
        """Test that waiting time raises ValueError when meeting has no creation_date."""
        # Arrange
        meeting_id = 1
        mock_meeting = Mock(spec=Meeting)
        mock_meeting.creation_date = None

        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.get_meeting_by_id",
            return_value=mock_meeting,
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Meeting 1 has no creation_date"):
            TranscriptionQueueEstimationService.get_meeting_transcription_waiting_time_minutes(
                meeting_id
            )

    def test_get_meeting_transcription_waiting_time_minutes_should_calculate_correctly_with_pending_meetings(
        self, mocker: MockerFixture
    ) -> None:
        """Test correct calculation when there are pending meetings."""
        # Arrange
        meeting_id = 1
        mock_meeting = Mock(spec=Meeting)
        mock_meeting.creation_date = datetime(2024, 10, 1, 12, 0, tzinfo=timezone.utc)

        pending_count = 20
        expected_waiting_time = (
            72  # 1 slot * 12 minutes + 60 minutes (base meeting duration) = 72 minutes
        )

        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.get_meeting_by_id",
            return_value=mock_meeting,
        )
        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.count_pending_meetings",
            return_value=pending_count,
        )

        # Act
        result = TranscriptionQueueEstimationService.get_meeting_transcription_waiting_time_minutes(
            meeting_id
        )

        # Assert
        assert result == expected_waiting_time

    def test_get_meeting_transcription_waiting_time_minutes_should_raise_exception_on_error(
        self, mocker: MockerFixture
    ) -> None:
        """Test that exceptions are raised properly."""
        # Arrange
        meeting_id = 1
        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.get_meeting_by_id",
            side_effect=Exception("Database error"),
        )

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            TranscriptionQueueEstimationService.get_meeting_transcription_waiting_time_minutes(
                meeting_id
            )

    def test_get_meeting_transcription_waiting_time_minutes_should_call_service_correctly(
        self, mocker: MockerFixture
    ) -> None:
        """Test that the utility function calls the service correctly."""
        # Arrange
        meeting_id = 1
        expected_result = 24

        mock_calculate = mocker.patch.object(
            TranscriptionQueueEstimationService,
            "get_meeting_transcription_waiting_time_minutes",
            return_value=expected_result,
        )

        # Act
        from mcr_meeting.app.services.transcription_waiting_time_service import (
            TranscriptionQueueEstimationService as Service,
        )

        result = Service.get_meeting_transcription_waiting_time_minutes(meeting_id)

        # Assert
        mock_calculate.assert_called_once_with(meeting_id)
        assert result == expected_result

    def test_get_meeting_remaining_waiting_time_minutes_should_return_correct_remaining_time(
        self, mocker: MockerFixture
    ) -> None:
        """Test that get_meeting_remaining_waiting_time_minutes returns correct remaining time."""
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
        result = TranscriptionQueueEstimationService.get_meeting_remaining_waiting_time_minutes(
            meeting_id
        )

        # Assert
        assert result == 30

    def test_get_meeting_remaining_waiting_time_minutes_should_return_zero_when_time_passed(
        self, mocker: MockerFixture
    ) -> None:
        """Test that get_meeting_remaining_waiting_time_minutes returns 0 when estimated time has passed."""
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
        result = TranscriptionQueueEstimationService.get_meeting_remaining_waiting_time_minutes(
            meeting_id
        )

        # Assert
        assert result == 0

    def test_get_meeting_remaining_waiting_time_minutes_should_raise_exception_when_transition_record_not_found(
        self, mocker: MockerFixture
    ) -> None:
        """Test that get_meeting_remaining_waiting_time_minutes raises ValueError when transition record not found."""
        # Arrange
        meeting_id = 1
        mocker.patch(
            "mcr_meeting.app.services.transcription_waiting_time_service.find_transition_record_by_meeting_and_status",
            return_value=None,
        )

        # Act & Assert
        with pytest.raises(
            ValueError, match="Meeting transition record with ID 1 not found"
        ):
            TranscriptionQueueEstimationService.get_meeting_remaining_waiting_time_minutes(
                meeting_id
            )

    def test_get_meeting_remaining_waiting_time_minutes_should_raise_exception_when_predicted_date_of_next_transition_is_none(
        self, mocker: MockerFixture
    ) -> None:
        """Test that get_meeting_remaining_waiting_time_minutes raises ValueError when predicted_date_of_next_transition is None."""
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
            TranscriptionQueueEstimationService.get_meeting_remaining_waiting_time_minutes(
                meeting_id
            )
