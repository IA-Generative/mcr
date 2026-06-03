from pydantic import BaseModel
from pydantic.fields import Field


class MinutesSynthesisContent(BaseModel):
    open_points: list[str] = Field(
        default_factory=list,
        description=(
            "Liste des points en suspens : questions ouvertes laissées sans réponse, "
            "sujets attendus mais non abordés, contradictions non résolues. "
            "Chaque entrée est concise et autonome. Liste vide si rien de pertinent."
        ),
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description=(
            "Liste de 2 à 5 recommandations concrètes et actionnables pour la suite, "
            "basées strictement sur le contenu de la réunion (pas de conseils génériques). "
            "Liste vide si rien de pertinent."
        ),
    )
