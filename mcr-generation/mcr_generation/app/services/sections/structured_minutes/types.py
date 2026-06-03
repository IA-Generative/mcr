"""Modèles map-reduce de la section compte-rendu structuré (calqués sur topics)."""

from pydantic import BaseModel, Field

from mcr_generation.app.schemas.base import MinuteTheme


class MappedMinuteDecisionLLM(BaseModel):
    """Décision extraite d'un extrait par le LLM (phase map)."""

    decision: str = Field(
        ...,
        description=(
            "Décision ou action explicitement décidée dans cet extrait, "
            "formulée de manière claire et concise."
        ),
    )
    owner: str | None = Field(
        None,
        description=(
            "Personne ou équipe responsable de la décision/action. "
            "null si non évoqué explicitement."
        ),
    )
    due: str | None = Field(
        None,
        description=(
            "Échéance (date au format JJ/MM/AAAA ou formulation relative). "
            "null si non évoquée."
        ),
    )


class MappedMinuteThemeLLM(BaseModel):
    """Thématique extraite d'un extrait par le LLM (phase map)."""

    topic: str = Field(
        ...,
        description="Titre court de la thématique discutée dans cet extrait.",
    )
    topic_confidence: float = Field(
        ...,
        ge=0,
        le=1,
        description=(
            "Niveau de confiance (entre 0 et 1) indiquant à quel point la "
            "thématique est correctement identifiée (1 = très sûr)."
        ),
    )
    summary: str | None = Field(
        None,
        description=(
            "Résumé en 1-3 phrases de la thématique. null si rien de pertinent."
        ),
    )
    decisions: list[MappedMinuteDecisionLLM] = Field(
        default_factory=list,
        description=(
            "Décisions/actions explicitement décidées sur cette thématique. "
            "Liste vide si aucune décision n'a été prise."
        ),
    )


class MappedMinuteTheme(MappedMinuteThemeLLM):
    """Modèle interne : enrichit la sortie LLM avec l'id de l'extrait source."""

    chunk_id: int


class MappedMinutesLLM(BaseModel):
    """Wrapper LLM regroupant toutes les thématiques extraites d'un extrait."""

    themes: list[MappedMinuteThemeLLM] = Field(
        ...,
        description=(
            "Liste des thématiques détectées dans l'extrait analysé, "
            "chacune avec son résumé et ses décisions. Liste vide si aucune."
        ),
    )


class MinutesContent(BaseModel):
    """Sortie consolidée de la phase reduce."""

    themes: list[MinuteTheme] = Field(
        default_factory=list,
        description=(
            "Liste des thématiques consolidées de la réunion avec leurs "
            "décisions associées (responsable et échéance si évoqués)."
        ),
    )
