from mcr_meeting.app.schemas.report_generation import (
    DetailedSynthesisGenerationResponse,
    ReportDetailedDiscussion,
    ReportHeader,
    ReportParticipant,
)
from mcr_meeting.app.services.report_content.template_renderer import (
    render_markdown_template,
)


def _build_fake_synthesis() -> DetailedSynthesisGenerationResponse:
    return DetailedSynthesisGenerationResponse(
        header=ReportHeader(
            title="Réunion de lancement projet Alpha",
            objective="Définir le planning et les responsabilités",
            participants=[
                ReportParticipant(
                    speaker_id="s1",
                    name="Alice Dupont",
                    role="Chef de projet",
                    confidence=0.95,
                ),
                ReportParticipant(
                    speaker_id="s2",
                    name="Bob Martin",
                    role="Développeur",
                    confidence=0.88,
                ),
            ],
            next_meeting="2026-03-10",
        ),
        discussions_summary=[
            "Le planning du projet Alpha a été validé avec un lancement prévu le 15 mars.",
            "Le budget initial est confirmé à 50k€, avec une clause de revue à mi-parcours.",
            "Un risque identifié sur la disponibilité de l'équipe back-end en avril.",
        ],
        detailed_discussions=[
            ReportDetailedDiscussion(
                title="Planning du projet",
                key_ideas=[
                    "Le projet doit démarrer le 15 mars.",
                    "Phase 1 (MVP) prévue sur 6 semaines.",
                    "Phase 2 (fonctionnalités avancées) à cadrer après le MVP.",
                ],
                decisions=[
                    "Lancement confirmé au 15 mars.",
                    "Revue de mi-parcours planifiée au 15 avril.",
                ],
                actions=[
                    "Alice : envoyer le planning détaillé d'ici vendredi.",
                    "Bob : préparer l'environnement de développement.",
                ],
                focus_points=[
                    "Disponibilité de l'équipe back-end en avril (congés).",
                ],
            ),
            ReportDetailedDiscussion(
                title="Budget et ressources",
                key_ideas=[
                    "Budget initial validé à 50k€.",
                    "Possibilité de renfort externe si nécessaire.",
                ],
                decisions=[
                    "Budget approuvé sans réserve.",
                ],
                actions=[],
                focus_points=[
                    "Clause de revue budgétaire à mi-parcours.",
                ],
            ),
        ],
        to_do_list=[
            "Alice : envoyer le planning détaillé d'ici vendredi.",
            "Bob : préparer l'environnement de développement.",
        ],
        to_monitor_list=[
            "Disponibilité de l'équipe back-end en avril.",
            "Clause de revue budgétaire à mi-parcours.",
        ],
    )


EXPECTED_MARKDOWN = """\
# Réunion de lancement projet Alpha
## Synthèse des échanges
- Le planning du projet Alpha a été validé avec un lancement prévu le 15 mars.
- Le budget initial est confirmé à 50k€, avec une clause de revue à mi-parcours.
- Un risque identifié sur la disponibilité de l'équipe back-end en avril.

## Points de discussion détaillés
### Planning du projet
**Points-clés :**
- Le projet doit démarrer le 15 mars.
- Phase 1 (MVP) prévue sur 6 semaines.
- Phase 2 (fonctionnalités avancées) à cadrer après le MVP.

**Décisions :**
- Lancement confirmé au 15 mars.
- Revue de mi-parcours planifiée au 15 avril.

**Actions :**
- Alice : envoyer le planning détaillé d'ici vendredi.
- Bob : préparer l'environnement de développement.

**Points d'attention :**
- Disponibilité de l'équipe back-end en avril (congés).

### Budget et ressources
**Points-clés :**
- Budget initial validé à 50k€.
- Possibilité de renfort externe si nécessaire.

**Décisions :**
- Budget approuvé sans réserve.


**Points d'attention :**
- Clause de revue budgétaire à mi-parcours.

## Récapitulatif final
### À faire
- Alice : envoyer le planning détaillé d'ici vendredi.
- Bob : préparer l'environnement de développement.

### À suivre
- Disponibilité de l'équipe back-end en avril.
- Clause de revue budgétaire à mi-parcours.
"""


def test_render_detailed_synthesis_markdown() -> None:
    synthesis = _build_fake_synthesis()
    data = {
        "title": synthesis.header.title or "",
        **synthesis.model_dump(exclude={"header"}),
    }
    result = render_markdown_template("detailed_synthesis.md.jinja", data)
    assert result == EXPECTED_MARKDOWN


def test_generate_detailed_synthesis_docx() -> None:
    from docx import Document

    from mcr_meeting.app.services.docx_report_generation_service import (
        generate_detailed_synthesis_docx,
    )

    synthesis = _build_fake_synthesis()
    result = generate_detailed_synthesis_docx(synthesis, "Réunion Alpha")

    assert result.getvalue()  # non-empty BytesIO

    doc = Document(result)
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Synthèse des échanges" in full_text
    assert "Planning du projet" in full_text
    assert "Budget et ressources" in full_text
    assert "À faire" in full_text
    assert "À suivre" in full_text
