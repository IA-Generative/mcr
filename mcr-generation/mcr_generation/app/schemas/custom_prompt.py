from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from mcr_generation.app.services.metadata_collectors.base import CollectorId


class CollectorSection(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["collector"] = "collector"
    heading: str = Field(min_length=1)
    collector_id: CollectorId


class CustomSection(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["custom"] = "custom"
    heading: str = Field(min_length=1)
    instruction: str = Field(min_length=1)


SectionSpec = Annotated[
    CollectorSection | CustomSection,
    Field(discriminator="kind"),
]


class RewriterOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str | None = None
    sections: list[SectionSpec] = Field(min_length=1, max_length=6)
