from pydantic import BaseModel
from pydantic.fields import Field


class MinutesSynthesisContent(BaseModel):
    open_points: list[str] = Field(
        default_factory=list,
        description=(
            "Liste des points en suspens : questions ouvertes, sujets non tranchés ou "
            "à rediscuter, déduits des thèmes et de leurs décisions. "
            "Liste vide si aucun point en suspens."
        ),
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description=(
            "Liste de 2 à 5 recommandations concrètes et actionnables déduites des thèmes. "
            "Liste vide si rien de pertinent."
        ),
    )
