from pydantic.fields import Field
from pydantic.main import BaseModel

from mcr_generation.app.schemas.base import DetailedDiscussion


class MappedFollowUpAction(BaseModel):
    action: str = Field(
        ...,
        description=("Description de l'action à réaliser suite à la décision."),
    )
    owner: str | None = Field(
        None,
        description=("Personne ou équipe responsable de l'action."),
    )
    due_date: str | None = Field(
        None,
        description=(
            "Date limite pour réaliser l'action (format : JJ/MM/AAAA ou relatif i.e dans une semaine)."
        ),
    )
    justification: str | None = Field(
        None,
        description=("Explication de l'action (pourquoi elle est nécessaire)."),
    )
    relevance_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Niveau de pertinence de l'action (0 = peu pertinent, 1 = très pertinent).",
    )
    confidence_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Niveau de confiance dans la pertinence de l'action (0 = peu sûr, 1 = très sûr).",
    )


class MappedMonitoringPoint(BaseModel):
    monitoring_point: str = Field(
        ...,
        description=(
            "Description du point de vigilance à surveiller suite à la décision ou à la discussion. "
            "Peut être de quatre natures : "
            "(1) un risque à anticiper (ex. 'Risque de dépassement de budget si les délais glissent'), "
            "(2) une question ouverte non résolue (ex. 'Question ouverte : quelle équipe prend en charge la migration ?'), "
            "(3) une validation à obtenir (ex. 'Validation à obtenir : accord de la direction juridique avant signature'), "
            "(4) un point de suivi de mise en œuvre d'une décision (ex. 'Vérifier que le nouveau process de validation est bien appliqué par l'équipe d'ici fin mars')."
        ),
    )
    owner: str | None = Field(
        None,
        description=("Personne ou équipe responsable du point de surveillance."),
    )
    justification: str | None = Field(
        None,
        description=(
            "Explication du point de surveillance (pourquoi il est important)."
        ),
    )
    relevance_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Niveau de pertinence du point de surveillance (0 = peu pertinent, 1 = très pertinent).",
    )
    confidence_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Niveau de confiance dans la pertinence du point de surveillance (0 = peu sûr, 1 = très sûr).",
    )


class MappedDecision(BaseModel):
    decision: str = Field(
        ...,
        description=(
            "Texte de la décision prise, formulé sous forme de phrase claire et concise. "
            "Une décision correspond à un engagement ou une action convenue (faire ou ne pas faire quelque chose)."
        ),
    )
    decision_facts: list[str] = Field(
        default_factory=list,
        description=(
            "Liste de faits ou raisons ayant conduit à cette décision. "
            "Inclure UNIQUEMENT si ces faits ne sont PAS déjà évidents dans le titre du sujet ou contexte. "
            "Sinon renvoyer une liste vide."
        ),
    )
    decision_maker: str | None = Field(
        None,
        description=(
            "Nom ou rôle de la personne ou de la direction qui a pris la décision "
            "(ex. 'Jean Dupont', 'Direction Produit'). "
            "Si non mentionné explicitement, renvoyer null."
        ),
    )
    relevance_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Niveau de pertinence de la décision (0 = peu pertinent, 1 = très pertinent).",
    )
    confidence_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Niveau de confiance indiquant à quel point tu es certain que cette phrase est bien une décision (1 = très sûr, 0 = très incertain).",
    )
    followup_actions: list[MappedFollowUpAction] = Field(
        default_factory=list,
        description=(
            "Liste des actions concrètes à entreprendre suite à la décision "
            "(ex. 'envoyer le compte-rendu', 'planifier une réunion de suivi'). "
            "Si aucune action n'est précisée, renvoyer une liste vide."
        ),
    )

    monitoring_points: list[MappedMonitoringPoint] = Field(
        default_factory=list,
        description=(
            "Points de vigilance à surveiller suite à la décision "
            "(ex. 'retour client sur le prochain mois', 'impact sur la charge de travail de l'équipe'). "
            "Renvoyer une liste vide si aucun n'est précisé."
        ),
    )


class MappedTakeaway(BaseModel):
    takeaway: str = Field(
        ...,
        description=(
            "Texte de l'information importante énoncée, formulé sous forme de phrase claire et concise. "
            "Une information importante est un fait ou une idée clé extraite de la discussion qui mérite d'être retenue. "
            "Ne pas inclure les décisions ni les points de vigilance."
        ),
    )
    takeaway_details: str | None = Field(
        None,
        description=(
            "Détails associés à l'information importante énoncée. "
            "Si aucun détail n'est disponible, renvoyer null."
        ),
    )
    takeaway_quote: str | None = Field(
        None,
        description=(
            "Citation directe issue de la transcription qui appuie l'information importante énoncée. "
            "Si aucune citation n'est disponible pour une information importante, renvoyer null."
        ),
    )
    relevance_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Niveau de pertinence de l'information importante par rapport au sujet principal (1 = très pertinent, 0 = peu pertinent).",
    )
    confidence_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Niveau de confiance indiquant à quel point tu es certain que l'information importante est correcte (1 = très sûr, 0 = très incertain).",
    )


class MappedDetailedDiscussion(BaseModel):
    """
    Modèle de sortie pour une discussion de reunion avec ses détails et decisions extrait d'une transcription de réunion.
    """

    topic: str = Field(
        ...,
        description=(
            "Sujet de la discussion, formulé de manière courte et factuelle, "
            "sans intention ni interprétation (ex. 'Préparation de la démo de fin d'année', 'Optimisation du plan de recrutement') "
            "Si ce sujet est une reprise d'un sujet déjà traité plus tôt dans l'extrait, "
            "ajouter le suffixe '(reprise)' (ex. 'Préparation du séminaire (reprise)')."
        ),
    )
    topic_confidence: float = Field(
        ...,
        ge=0,
        le=1,
        description=(
            "Niveau de confiance (entre 0 et 1) indiquant à quel point tu es certain "
            "que le sujet est correctement identifié (1 = très sûr, 0 = très incertain)."
        ),
    )
    takeaways: list[MappedTakeaway] = Field(
        default_factory=list,
        description=(
            "Liste des détails pertinents sur le sujet discuté (contexte, enjeux, contraintes, objectifs)."
            "Si aucun détail pertinent ou si redondant avec introduction_text, titre ou main_decision, renvoyer une liste vide."
        ),
    )
    decisions: list[MappedDecision] = Field(
        default_factory=list,
        description=(
            "Liste des décisions associées à ce sujet, chacune avec ses métadonnées "
            "(texte, responsable, actions de suivi, etc.)."
            "Si aucune décision n'est prise sur ce sujet, renvoyer une liste vide."
        ),
    )
    chunk_id: int = Field(
        default=0,
        description=(
            "Identifiant du segment de transcript d'où provient cette décision. "
            "Permet de relier chaque décision à son extrait source. "
            "Ce champ est renseigné automatiquement, ne pas le remplir."
        ),
    )


class MappedDetailedDiscussions(BaseModel):
    """
    Modèle regroupant l'ensemble des discussions détaillées extraites d'un même extrait
    de transcription.
    """

    detailed_discussions: list[MappedDetailedDiscussion] = Field(
        default_factory=list,
        description=(
            "Liste de toutes les discussions détaillées détectées dans l'extrait de "
            "transcription analysé, dans l'ordre chronologique d'apparition. "
            "Chaque entrée correspond à une discussion détaillée avec ses faits et "
            "métadonnées (chunk_id, score de confiance etc). "
        ),
    )


class Content(BaseModel):
    detailed_discussions: list[DetailedDiscussion] = Field(
        default_factory=list,
        description=(
            "Liste des discussions détaillées extraites de la transcription d'une réunion, avec leurs détails et décisions associées."
        ),
    )
