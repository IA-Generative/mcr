from typing import Optional

from pydantic import BaseModel, Field

from mcr_generation.app.schemas.base import Topic


class MappedFollowUpAction(BaseModel):
    action: str = Field(
        ...,
        description=("Description de l'action à réaliser suite à la décision."),
    )
    owner: Optional[str] = Field(
        None,
        description=("Personne ou équipe responsable de l'action."),
    )
    due_date: Optional[str] = Field(
        None,
        description=(
            "Date limite pour réaliser l'action (format : JJ/MM/AAAA ou relatif i.e dans une semaine)."
        ),
    )
    justification: Optional[str] = Field(
        None,
        description=("Explication de l'action (pourquoi elle est nécessaire)."),
    )
    relevance_score: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description=(
            "Niveau de pertinence de l'action (0 = peu pertinent, 1 = très pertinent)."
        ),
    )
    confidence_score: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description=(
            "Niveau de confiance dans la pertinence de l'action (0 = peu sûr, 1 = très sûr)."
        ),
    )


class MappedDecision(BaseModel):
    decision: str = Field(
        ...,
        description=(
            "Texte de la décision prise, formulé sous forme de phrase claire et concise. "
            "Une décision correspond à un engagement ou une action convenue (faire ou ne pas faire quelque chose)."
        ),
    )
    decision_facts: Optional[list[str]] = Field(
        None,
        description=(
            "Liste de faits ou raisons ayant conduit à cette décision. "
            "Inclure UNIQUEMENT si ces faits ne sont PAS déjà évidents dans le titre du sujet ou contexte. "
            "Sinon renvoyer une liste vide."
        ),
    )
    decision_maker: Optional[str] = Field(
        None,
        description=(
            "Nom ou rôle de la personne ou de la direction qui a pris la décision "
            "(ex. 'Jean Dupont', 'Direction Produit'). "
            "Si non mentionné explicitement, renvoyer null."
        ),
    )
    decision_confidence: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description=(
            "Niveau de confiance (entre 0 et 1) indiquant à quel point tu es certain "
            "que cette phrase est bien une décision (1 = très sûr, 0 = très incertain)."
        ),
    )
    decision_relevance: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description=(
            "Niveau de pertinence de la décision (0 = peu pertinent, 1 = très pertinent)."
        ),
    )

    followup_actions: Optional[list[MappedFollowUpAction]] = Field(
        None,
        description=(
            "Liste des actions concrètes à entreprendre suite à la décision "
            "(ex. 'envoyer le compte-rendu', 'planifier une réunion de suivi'). "
            "Si aucune action n’est précisée, renvoyer une liste vide."
        ),
    )


class MappedTopicDetails(BaseModel):
    subtopic: Optional[str] = Field(
        None,
        description=(
            "Sous-sujet correspondant a un aspect spécifique du sujet principal (ex. 'budget 2024', 'lancement produit X'). "
            "Mettre null si le sujet principal est suffisamment précis."
        ),
    )
    facts: list[str] = Field(
        default_factory=list,
        description=(
            "Liste de faits ATOMIQUES principaux (max 5 faits, 1 idée par item). "
            "Style factuel et concis, sans redondance avec topic ni decisions. "
            "Inclure UNIQUEMENT les informations les plus pertinentes."
        ),
    )
    facts_justification: list[Optional[str]] = Field(
        default_factory=list,
        description=(
            "Liste des justifications ou explications associées à chaque fait énoncé. "
            "Si aucune justification n’est disponible pour un fait, renvoyer null pour cet item."
        ),
    )
    facts_quotes: list[Optional[str]] = Field(
        default_factory=list,
        description=(
            "Liste des citations directes issues de la transcription qui appuient chaque fait énoncé. "
            "Si aucun citation n’est disponible pour un fait, renvoyer null pour cet item."
        ),
    )
    facts_relevance: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description=(
            "Niveau de pertinence des faits par rapport au sujet principal (1 = très pertinent, 0 = peu pertinent)."
        ),
    )
    facts_confidence: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description=(
            "Niveau de confiance (entre 0 et 1) indiquant à quel point tu es certain "
            "que les faits sont corrects (1 = très sûr, 0 = très incertain)."
        ),
    )


class MappedTopic(BaseModel):
    """
    Modèle de sortie pour un sujet de reunion avec ses details et decisions extrait d’une transcription de réunion.
    """

    topic: str = Field(
        ...,
        description=(
            "Sujet ou domaine de la décision (ex. 'budget', 'lancement produit'). "
            "Si non mentionné, renvoyer null."
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
    details: MappedTopicDetails = Field(
        ...,
        description=(
            "Détails pertinents sur le sujet discuté (contexte, enjeux, contraintes, objectifs)."
        ),
    )
    decisions: list[MappedDecision] = Field(
        ...,
        description=(
            "Liste des décisions associées à ce sujet, chacune avec ses métadonnées "
            "(texte, responsable, actions de suivi, etc.)."
            "Si aucune décision n’est prise sur ce sujet, renvoyer une liste vide."
        ),
    )
    chunk_id: int = Field(
        ...,
        description=(
            "Identifiant du segment de transcript d'où provient cette décision. "
            "Permet de relier chaque décision à son extrait source."
        ),
    )


class MappedTopics(BaseModel):
    """
    Modèle regroupant l'ensemble des décisions extraites d'un même extrait
    de transcription.
    """

    topics: list[MappedTopic] = Field(
        ...,
        description=(
            "Liste de toutes les sujets détectées dans l'extrait de "
            "transcription analysé. Chaque entrée correspond à un sujet unique avec  "
            "avec ses faits et métadonnées (chunk_id, score de confiance etc)."
        ),
    )


class Content(BaseModel):
    topics: list[Topic] = Field(
        ...,
        description=(
            "Liste des sujets discutés lors de la réunion avec leur détails et décisions associées."
        ),
    )
    next_steps: list[str] = Field(
        ...,
        description=(
            "Liste des prochaines étapes suite à la réunion."
            "Ne reprend pas les actions de suivi associées aux décisions precedemments extraites."
            "Renvoyer une liste vide si aucune prochaine étape supplémentaire n'a été identifiée."
            ""
        ),
    )
