from pydantic import BaseModel
from pydantic.fields import Field


class NarrativeChunk(BaseModel):
    """Reformulation narrative (discours indirect) d'un segment de transcription."""

    narrative: str = Field(
        ...,
        description=(
            "Version reformulée du segment en discours indirect « X a dit que Y », "
            "ordre chronologique conservé, sans analyse ni préambule, en français."
        ),
    )
