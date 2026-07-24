from mcr_meeting.app.models.deliverable_model import DeliverableType

_FILENAME_LABEL_BY_TYPE: dict[DeliverableType, str] = {
    DeliverableType.DECISION_RECORD: "Releve_Decision",
    DeliverableType.DETAILED_SYNTHESIS: "Synthese_Detaillee",
    DeliverableType.CUSTOM_REPORT: "Compte_Rendu_Personnalise",
    DeliverableType.TRANSCRIPTION: "Transcription",
    DeliverableType.STRUCTURED_MINUTES: "Compte_Rendu_Structure",
}


def build_deliverable_filename(
    deliverable_type: DeliverableType, meeting_name: str
) -> str:
    return f"{_FILENAME_LABEL_BY_TYPE[deliverable_type]}_{meeting_name}.docx"
