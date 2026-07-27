from pydantic import BaseModel, Field

from mcr_generation.app.schemas.base import MinuteTheme


class MappedMinuteDecisionLLM(BaseModel):
    decision: str = Field(
        ...,
        description=(
            "Décision ou action actée dans l'extrait, formulée de manière claire et concise."
        ),
    )
    owner: str | None = Field(
        None,
        description=(
            "Responsable de la décision/action si nommé ou trivialement déductible. "
            "null sinon."
        ),
    )
    due: str | None = Field(
        None,
        description=(
            "Échéance telle qu'écrite (ex. '15/09', 'fin de semaine'). null si absente."
        ),
    )


class MappedMinuteThemeLLM(BaseModel):
    topic: str = Field(..., description="Titre court de la thématique discutée.")
    topic_confidence: float = Field(
        ...,
        ge=0,
        le=1,
        description=(
            "Niveau de confiance (entre 0 et 1) indiquant à quel point ce thème est "
            "pertinent pour le compte-rendu final."
        ),
    )
    summary: str | None = Field(
        None,
        description="Résumé factuel de 1 à 3 phrases. null si rien de pertinent.",
    )
    decisions: list[MappedMinuteDecisionLLM] = Field(
        default_factory=list,
        description=(
            "Décisions ou actions associées à ce thème. Liste vide si aucune décision."
        ),
    )


class MappedMinuteTheme(MappedMinuteThemeLLM):
    chunk_id: int


class MappedMinutesLLM(BaseModel):
    themes: list[MappedMinuteThemeLLM] = Field(
        ...,
        description=(
            "Liste des thématiques détectées dans l'extrait de transcription analysé, "
            "chacune avec ses décisions associées."
        ),
    )


class MinutesContent(BaseModel):
    themes: list[MinuteTheme] = Field(default_factory=list)
