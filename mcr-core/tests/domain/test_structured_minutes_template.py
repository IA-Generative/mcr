from mcr_meeting.app.domain.markdown_to_docx import render_markdown_template

_TEMPLATE = "structured_minutes.md.jinja"


def _full_data() -> dict:  # type: ignore[type-arg]
    return {
        "title": "Refonte du portail client",
        "objective": "Décider du périmètre du MVP",
        "participants": [
            {"speaker_id": "LOCUTEUR_01", "name": "Claire Martin", "role": "PO"},
            {"speaker_id": "LOCUTEUR_02", "name": None, "role": None},
        ],
        "next_meeting": "Jeudi 31/07 à 14h",
        "themes": [
            {
                "title": "Périmètre du MVP",
                "summary": "Le MVP se limite à l'auth.",
                "decisions": [
                    {"item": "Exclure la messagerie", "owner": "Claire", "due": "15/09"}
                ],
            }
        ],
        "open_points": ["Choix de l'hébergeur non tranché."],
        "recommendations": ["Cadrer la messagerie en lot 2."],
    }


def test_renders_all_sections() -> None:
    rendered = render_markdown_template(_TEMPLATE, _full_data())

    assert "# Refonte du portail client" in rendered
    assert "## Objectif" in rendered
    assert "## Participants" in rendered
    assert "- Claire Martin — PO" in rendered
    assert "- LOCUTEUR_02" in rendered
    assert "## Thèmes" in rendered
    assert "### Périmètre du MVP" in rendered
    assert "- Exclure la messagerie — resp. Claire — échéance 15/09" in rendered
    assert "## Points en suspens" in rendered
    assert "## Recommandations" in rendered
    assert "## Prochaine réunion" in rendered


def test_empty_collections_render_fallback_labels() -> None:
    data = _full_data()
    data["themes"] = []
    data["open_points"] = []
    data["recommendations"] = []

    rendered = render_markdown_template(_TEMPLATE, data)

    assert "- Aucun thème identifié." in rendered
    assert "- Aucun point en suspens identifié." in rendered
    assert "- Aucune recommandation." in rendered


def test_empty_header_hides_header_blocks() -> None:
    data = _full_data()
    data["objective"] = None
    data["participants"] = []
    data["next_meeting"] = None

    rendered = render_markdown_template(_TEMPLATE, data)

    assert "## Objectif" not in rendered
    assert "## Participants" not in rendered
    assert "## Prochaine réunion" not in rendered
