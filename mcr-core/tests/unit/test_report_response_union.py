from pydantic import TypeAdapter

from mcr_meeting.app.schemas.report_generation import (
    DetailedSynthesisGenerationResponse,
    ReportResponse,
    StructuredMinutesResponse,
)

_STRUCTURED_MINUTES_PAYLOAD = {
    "header": {
        "title": "Refonte du portail client",
        "objective": "Décider du périmètre du MVP",
        "participants": [
            {
                "speaker_id": "LOCUTEUR_01",
                "name": "Claire Martin",
                "role": "PO",
                "confidence": 0.9,
            }
        ],
        "next_meeting": "Jeudi 31/07 à 14h, salle B",
    },
    "themes": [
        {
            "title": "Périmètre du MVP",
            "summary": "Le MVP se limite à l'auth.",
            "decisions": [
                {"item": "Exclure la messagerie", "owner": "Claire Martin", "due": None}
            ],
        }
    ],
    "open_points": ["Le choix de l'hébergeur n'est pas tranché."],
    "recommendations": ["Cadrer la messagerie en lot 2."],
}

_DETAILED_SYNTHESIS_PAYLOAD = {
    "header": {
        "title": "Réu",
        "objective": None,
        "participants": [],
        "next_meeting": None,
    },
    "discussions_summary": ["point"],
    "detailed_discussions": [],
    "to_do_list": [],
    "to_monitor_list": [],
}


def test_structured_minutes_payload_resolves_to_structured_minutes() -> None:
    result = TypeAdapter(ReportResponse).validate_python(_STRUCTURED_MINUTES_PAYLOAD)

    assert isinstance(result, StructuredMinutesResponse)
    assert result.header.objective == "Décider du périmètre du MVP"
    assert result.themes[0].title == "Périmètre du MVP"
    assert result.themes[0].decisions[0].owner == "Claire Martin"
    assert result.open_points == ["Le choix de l'hébergeur n'est pas tranché."]


def test_detailed_synthesis_payload_is_not_captured_by_structured_minutes() -> None:
    result = TypeAdapter(ReportResponse).validate_python(_DETAILED_SYNTHESIS_PAYLOAD)

    assert isinstance(result, DetailedSynthesisGenerationResponse)
