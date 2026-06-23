from pydantic import BaseModel, ConfigDict, Field


class Intent(BaseModel):
    """
    Modèle de sortie pour l'extraction du titre et de l'objet d'une réunion
    à partir d'une transcription diarizée. Toutes les informations doivent être
    formulées en français, de manière concise et factuelle.
    """

    title: str | None = Field(
        None,
        description=(
            "Titre de la réunion. Doit être court, spécifique et cohérent avec le sujet dominant extrait ou déduit de la transcription"
            "Renvoie null si aucun titre n'est explicitement mentionné ou ne peut être raisonnablement déduit."
        ),
    )

    objective: str | None = Field(
        None,
        description=(
            "Objet principal de la réunion. Une phrase très concise résumant le but de la séance, "
            "soit explicitement mentionné, soit déduit à partir des discussions dominantes."
        ),
    )

    confidence: float | None = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Niveau de confiance (entre 0 et 1) reflétant dans quelle mesure le titre et l’objet "
            "sont fiables et bien étayés par la transcription. Une valeur basse indique une forte incertitude "
            "ou un manque d’informations explicites."
        ),
    )

    justification: str | None = Field(
        description=(
            "Justification brève expliquant pourquoi ce titre et cet objet ont été retenus. "
            "Doit citer les signaux clés de la transcription : mots-clés, thèmes récurrents, "
            "mentions explicites, ou déductions raisonnables basées sur le contenu."
        ),
    )


class NextMeeting(BaseModel):
    """
    Modèle de sortie pour l'extraction des informations sur la prochaine réunion
    à partir d'une transcription diarizée. Toutes les informations doivent être
    formulées en français, de manière concise et factuelle.
    """

    date: str | None = Field(
        None,
        description=(
            "Date prévue de la prochaine réunion au format 'JJ/MM/AAAA' ou en relatif (mardi prochain). "
            "Renvoie null si la date n'est pas explicitement mentionnée ou ne peut être raisonnablement déduite."
        ),
    )

    time: str | None = Field(
        None,
        description=(
            "Heure prévue de la prochaine réunion au format 'HH:MM' ou relatif (ex: 'même heure', 'en matinée'). "
            "Renvoie null si l'heure n'est pas explicitement mentionnée ou ne peut être raisonnablement déduite."
        ),
    )

    purpose: str | None = Field(
        None,
        description=(
            "Objet principal ou but de la prochaine réunion. Une phrase très concise résumant le but prévu, "
            "soit explicitement mentionné, soit déduit à partir des discussions dominantes."
        ),
    )
    confidence: float | None = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Niveau de confiance (entre 0 et 1) reflétant dans quelle mesure les informations sur la prochaine réunion "
            "sont fiables et bien étayées par la transcription. Une valeur basse indique une forte incertitude "
            "ou un manque d’informations explicites."
        ),
    )
    justification: str | None = Field(
        description=(
            "Justification brève expliquant pourquoi ces informations ont été retenues. "
            "Doit citer les signaux clés de la transcription : mots-clés, thèmes récurrents, "
            "mentions explicites, ou déductions raisonnables basées sur le contenu."
        ),
    )


class Participant(BaseModel):
    speaker_id: str = Field(
        description="Identifiant unique du locuteur dans la transcription ex: LOCUTEUR_03.",
    )
    name: str | None = Field(
        None,
        description="Prenom et/ou nom déduit pour le locuteur à partir des interactions dans la transcription. Ex: 'Jean' ou 'Jean Dupont'.",
    )
    role: str | None = Field(
        None,
        description="Fonction/rôle si mentionné ou déduit (ex. PO, Tech Lead, Directeur financier).",
    )
    confidence: float | None = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Niveau de confiance (entre 0 et 1) indiquant à quel point tu es certain du nom associé locuteur. null si aucune association n'est faite.",
    )


class ParticipantWithThinking(Participant):
    """LLM-internal participant carrying chain-of-thought reasoning.

    Used during the refine loop so the LLM can read its prior reasoning when
    evaluating new chunks. Required-but-nullable: the LLM must explicitly emit
    a string or null — a missing key indicates a malformed response.
    """

    association_justification: str | None = Field(
        ...,
        description=(
            "Identification explicite ou déduction par contexte ayant permis d'associer ce nom/rôle au locuteur avec l'id. "
            "null si aucun indice pertinent."
        ),
    )


class Participants(BaseModel):
    participants: list[Participant] = Field(
        ...,
        description="Liste des participants identifiés dans la réunion.",
    )


class ParticipantsWithThinkingListWrapper(BaseModel):
    participants: list[ParticipantWithThinking] = Field(
        ...,
        description="Liste des participants identifiés dans la réunion avec un speaker_id unique avec leur nom ou role si disponible. Si aucun participant n'a pu être identifié, renvoyer une liste vide.",
    )

    def to_public(self) -> Participants:
        return Participants(
            participants=[
                Participant(
                    speaker_id=p.speaker_id,
                    name=p.name,
                    role=p.role,
                    confidence=p.confidence,
                )
                for p in self.participants
            ]
        )


class Decision(BaseModel):
    text: str = Field(
        ...,
        description=(
            "Décision extraite du texte, reformulée de manière claire et concise en spécifiant le responsable de la décision si explicite ou détecté."
        ),
    )
    followup_actions: list[str] | None = Field(
        None,
        description=(
            "Liste des actions concrètes à entreprendre suite à la décision "
            "(ex. 'envoyer le compte-rendu', 'planifier une réunion de suivi'). "
            "Si aucune action n’est précisée, ou que l'action est la meme que la decision dans laquelle elle s'inscrit, alors renvoyer une liste vide."
        ),
    )


class Topic(BaseModel):
    title: str = Field(
        ...,
        description=(
            "Titre court et explicite du sujet de discussion regroupant les décisions "
            "associées (ex. 'Budget 2025', 'Stratégie de lancement produit', "
            "'Migration vers le cloud')."
        ),
    )
    introduction_text: str | None = Field(
        ...,
        description=(
            "Phrase introductive présentant le sujet et son contexte, "
            "sans être redondante avec le titre ou les détails."
            "Si aucune information pertinente n’est disponible, renvoyer None."
        ),
    )
    details: list[str] = Field(
        ...,
        description=(
            "Faits concrets et pertinents sur le sujet discuté (contexte, chiffres, contraintes, objectifs). "
            "Maximum 2-3 phrases courtes. Chaque phrase doit être factuelle et apporter une information concrète. "
            "Renvoyer une liste vide si aucun détail pertinent ou si redondant avec introduction_text, titre ou main_decision. "
            "ÉLIMINER toute redondance entre titre/introduction/détails/décision."
        ),
    )
    main_decision: str | None = Field(
        None,
        description=(
            "Décision principale relative au sujet, incluant le décideur si connu et l'action de suivi si applicable. "
            "Format concis: '[Décideur] a décidé de [action] [+ suivi]'. "
            "Mettre None si aucune décision n'a été prise. "
            "NE PAS reformuler un détail déjà mentionné."
        ),
    )


class Header(BaseModel):
    title: str | None
    objective: str | None
    participants: list[Participant]
    next_meeting: str | None


class BaseReport(BaseModel):
    header: Header


class DecisionRecord(BaseReport):
    topics_with_decision: list[Topic]
    next_steps: list[str]


class DetailedDiscussion(BaseModel):
    title: str
    key_ideas: list[str]
    decisions: list[str]
    actions: list[str]
    focus_points: list[str]


class DetailedSynthesis(BaseReport):
    discussions_summary: list[str]
    detailed_discussions: list[DetailedDiscussion]
    to_do_list: list[str]
    to_monitor_list: list[str]


class CustomMarkdownReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    markdown_content: str


class MinuteDecision(BaseModel):
    """Décision ou action décidée pendant la réunion."""

    item: str = Field(
        ...,
        description="La décision ou l'action décidée, formulée de manière claire et concise.",
    )
    owner: str | None = Field(
        None,
        description="Personne ou équipe responsable de la décision/action. null si non évoqué.",
    )
    due: str | None = Field(
        None,
        description="Échéance (date au format JJ/MM/AAAA ou formulation relative). null si non évoquée.",
    )


class MinuteTheme(BaseModel):
    """Thématique discutée avec ses décisions associées."""

    title: str = Field(..., description="Titre court de la thématique.")
    summary: str | None = Field(
        None,
        description="Résumé en 1-3 phrases de la thématique. null si rien de pertinent.",
    )
    decisions: list[MinuteDecision] = Field(
        default_factory=list,
        description="Décisions/actions explicitement décidées sur cette thématique.",
    )


class StructuredMinutes(BaseReport):
    """Compte-rendu structuré (thèmes, décisions, points en suspens, recommandations)."""

    themes: list[MinuteTheme]
    open_points: list[str]
    recommendations: list[str]
