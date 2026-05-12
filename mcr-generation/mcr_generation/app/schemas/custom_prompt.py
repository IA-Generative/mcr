from pydantic import BaseModel, ConfigDict, Field, model_validator


class SectionSpec(BaseModel):
    """One section of the requested custom report.

    Either delegates to a predefined metadata collector (collector_id set,
    instruction null) or runs the generic pipeline with a free-text instruction.
    """

    model_config = ConfigDict(frozen=True)

    heading: str = Field(min_length=1)
    collector_id: str | None = None
    instruction: str | None = None

    @model_validator(mode="after")
    def _exactly_one_source(self) -> "SectionSpec":
        if (self.collector_id is None) == (self.instruction is None):
            raise ValueError(
                "SectionSpec requires exactly one of collector_id or instruction."
            )
        return self


class RewriterOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str | None = None
    sections: list[SectionSpec] = Field(min_length=1, max_length=6)
