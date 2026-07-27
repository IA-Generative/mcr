from mcr_meeting.app.domain.markdown_to_docx import render_markdown_template

_TEMPLATE = "structured_minutes.md.jinja"


def _full_data() -> dict:  # type: ignore[type-arg]
    return {
        "title": "Refonte du portail client",
        "report": {
            "header": {
                "objective": "Décider du périmètre du MVP",
                "participants": [
                    {
                        "speaker_id": "LOCUTEUR_01",
                        "name": "Claire Martin",
                        "role": "PO",
                    },
                    {"speaker_id": "LOCUTEUR_02", "name": None, "role": None},
                ],
                "next_meeting": "Jeudi 31/07 à 14h",
            },
            "themes": [
                {
                    "title": "Périmètre du MVP",
                    "summary": "Le MVP se limite à l'auth.",
                    "decisions": [
                        {
                            "item": "Exclure la messagerie",
                            "owner": "Claire",
                            "due": "15/09",
                        }
                    ],
                }
            ],
            "open_points": ["Choix de l'hébergeur non tranché."],
            "recommendations": ["Cadrer la messagerie en lot 2."],
        },
    }


def test_renders_all_sections() -> None:
    rendered = render_markdown_template(_TEMPLATE, _full_data())
    lines = rendered.splitlines()

    assert "# Refonte du portail client" in rendered
    assert "## Objectif" in rendered
    assert "## Participants" in rendered
    # Line-level (not substring): a merged "- Claire Martin — PO- LOCUTEUR_02"
    # would still contain both substrings, so it would hide the merging bug.
    assert "- Claire Martin — PO" in lines
    assert "- LOCUTEUR_02" in lines
    assert "## Thèmes" in rendered
    assert "### Périmètre du MVP" in rendered
    assert "- Exclure la messagerie — resp. Claire — échéance 15/09" in lines
    assert "## Points en suspens" in rendered
    assert "## Recommandations" in rendered
    assert "## Prochaine réunion" in rendered


def test_consecutive_bullets_and_following_heading_stay_separate() -> None:
    # Regression: bullet lines ending in an inline {% endif %} lost their
    # newline under trim_blocks, merging items and swallowing the next theme
    # heading (e.g. "...échéance 01/01- Décision A2" / "...### Thème B").
    data = _full_data()
    data["report"]["themes"] = [
        {
            "title": "Thème A",
            "summary": None,
            "decisions": [
                {"item": "Décision A1", "owner": "Alice", "due": "01/01"},
                {"item": "Décision A2", "owner": None, "due": None},
            ],
        },
        {
            "title": "Thème B",
            "summary": None,
            "decisions": [{"item": "Décision B1", "owner": None, "due": None}],
        },
    ]

    lines = render_markdown_template(_TEMPLATE, data).splitlines()

    assert "- Claire Martin — PO" in lines
    assert "- LOCUTEUR_02" in lines
    assert "- Décision A1 — resp. Alice — échéance 01/01" in lines
    assert "- Décision A2" in lines
    assert "### Thème A" in lines
    assert "### Thème B" in lines


def test_empty_collections_render_fallback_labels() -> None:
    data = _full_data()
    data["report"]["themes"] = []
    data["report"]["open_points"] = []
    data["report"]["recommendations"] = []

    rendered = render_markdown_template(_TEMPLATE, data)

    assert "- Aucun thème identifié." in rendered
    assert "- Aucun point en suspens identifié." in rendered
    assert "- Aucune recommandation." in rendered


def test_empty_header_hides_header_blocks() -> None:
    data = _full_data()
    data["report"]["header"]["objective"] = None
    data["report"]["header"]["participants"] = []
    data["report"]["header"]["next_meeting"] = None

    rendered = render_markdown_template(_TEMPLATE, data)

    assert "## Objectif" not in rendered
    assert "## Participants" not in rendered
    assert "## Prochaine réunion" not in rendered
