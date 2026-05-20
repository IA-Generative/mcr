import pytest

from mcr_meeting.app.models.deliverable_model import DeliverableType
from mcr_meeting.app.utils.deliverable_filename import build_deliverable_filename


@pytest.mark.parametrize(
    ("deliverable_type", "expected_prefix"),
    [
        (DeliverableType.DECISION_RECORD, "Releve_Decision"),
        (DeliverableType.DETAILED_SYNTHESIS, "Synthese_Detaillee"),
        (DeliverableType.CUSTOM_REPORT, "Compte_Rendu_Personnalise"),
        (DeliverableType.TRANSCRIPTION, "Transcription"),
    ],
)
def test_builds_expected_label_per_type(
    deliverable_type: DeliverableType, expected_prefix: str
) -> None:
    assert (
        build_deliverable_filename(
            deliverable_type=deliverable_type, meeting_name="meeting"
        )
        == f"{expected_prefix}_meeting.docx"
    )


def test_preserves_accented_meeting_name() -> None:
    assert (
        build_deliverable_filename(
            deliverable_type=DeliverableType.DECISION_RECORD,
            meeting_name="Réunion équipe",
        )
        == "Releve_Decision_Réunion équipe.docx"
    )


def test_preserves_meeting_name_with_special_chars() -> None:
    assert (
        build_deliverable_filename(
            deliverable_type=DeliverableType.TRANSCRIPTION,
            meeting_name="Q1/Q2 review",
        )
        == "Transcription_Q1/Q2 review.docx"
    )


def test_empty_meeting_name_does_not_crash() -> None:
    assert (
        build_deliverable_filename(
            deliverable_type=DeliverableType.TRANSCRIPTION,
            meeting_name="",
        )
        == "Transcription_.docx"
    )
