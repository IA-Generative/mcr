from pytest_mock import MockerFixture

from mcr_meeting.app.services.speech_to_text.participants_naming.participant_extraction import (
    Participant,
    ParticipantExtraction,
)

_LOGGER_PATH = (
    "mcr_meeting.app.services.speech_to_text.participants_naming."
    "participant_extraction.logger"
)


def _make_participant(
    speaker_id: str,
    name: str | None,
    confidence: float = 0.9,
) -> Participant:
    return Participant(
        speaker_id=speaker_id,
        name=name,
        role=None,
        confidence=confidence,
        association_justification=None,
    )


class TestWarnOnNameLoss:
    """Tests for ParticipantExtraction._warn_on_name_loss."""

    def test_warns_when_known_name_becomes_none(self, mocker: MockerFixture) -> None:
        mock_logger = mocker.patch(_LOGGER_PATH)
        previous = [_make_participant("LOCUTEUR_01", name="Alice")]
        current = [_make_participant("LOCUTEUR_01", name=None)]

        ParticipantExtraction._warn_on_name_loss(
            previous=previous, current=current, step_index=2
        )

        mock_logger.warning.assert_called_once()
        message, *args = mock_logger.warning.call_args.args
        assert "lost their name" in message
        assert args == ["LOCUTEUR_01", 2, "Alice"]

    def test_warns_when_known_participant_disappears(
        self, mocker: MockerFixture
    ) -> None:
        mock_logger = mocker.patch(_LOGGER_PATH)
        previous = [_make_participant("LOCUTEUR_01", name="Alice")]
        current: list[Participant] = []

        ParticipantExtraction._warn_on_name_loss(
            previous=previous, current=current, step_index=3
        )

        mock_logger.warning.assert_called_once()
        message, *args = mock_logger.warning.call_args.args
        assert "disappeared" in message
        assert args == ["LOCUTEUR_01", "Alice", 3]

    def test_does_not_warn_when_name_is_preserved(self, mocker: MockerFixture) -> None:
        mock_logger = mocker.patch(_LOGGER_PATH)
        previous = [_make_participant("LOCUTEUR_01", name="Alice")]
        current = [_make_participant("LOCUTEUR_01", name="Alice")]

        ParticipantExtraction._warn_on_name_loss(
            previous=previous, current=current, step_index=1
        )

        mock_logger.warning.assert_not_called()

    def test_does_not_warn_when_previous_name_was_already_none(
        self, mocker: MockerFixture
    ) -> None:
        mock_logger = mocker.patch(_LOGGER_PATH)
        previous = [_make_participant("LOCUTEUR_01", name=None)]
        current = [_make_participant("LOCUTEUR_01", name=None)]

        ParticipantExtraction._warn_on_name_loss(
            previous=previous, current=current, step_index=1
        )

        mock_logger.warning.assert_not_called()

    def test_does_not_warn_when_previous_was_none_and_disappears(
        self, mocker: MockerFixture
    ) -> None:
        mock_logger = mocker.patch(_LOGGER_PATH)
        previous = [_make_participant("LOCUTEUR_01", name=None)]
        current: list[Participant] = []

        ParticipantExtraction._warn_on_name_loss(
            previous=previous, current=current, step_index=1
        )

        mock_logger.warning.assert_not_called()

    def test_does_not_warn_for_newly_added_participant(
        self, mocker: MockerFixture
    ) -> None:
        mock_logger = mocker.patch(_LOGGER_PATH)
        previous: list[Participant] = []
        current = [_make_participant("LOCUTEUR_01", name="Alice")]

        ParticipantExtraction._warn_on_name_loss(
            previous=previous, current=current, step_index=1
        )

        mock_logger.warning.assert_not_called()

    def test_warns_for_each_affected_participant(self, mocker: MockerFixture) -> None:
        mock_logger = mocker.patch(_LOGGER_PATH)
        previous = [
            _make_participant("LOCUTEUR_01", name="Alice"),
            _make_participant("LOCUTEUR_02", name="Bob"),
            _make_participant("LOCUTEUR_03", name="Charlie"),
        ]
        current = [
            _make_participant("LOCUTEUR_01", name="Alice"),
            _make_participant("LOCUTEUR_02", name=None),
        ]

        ParticipantExtraction._warn_on_name_loss(
            previous=previous, current=current, step_index=4
        )

        assert mock_logger.warning.call_count == 2
        warned_speaker_ids = {
            call.args[1] for call in mock_logger.warning.call_args_list
        }
        assert warned_speaker_ids == {"LOCUTEUR_02", "LOCUTEUR_03"}
