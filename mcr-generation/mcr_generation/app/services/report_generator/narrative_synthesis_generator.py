from typing import ClassVar

import instructor
from langfuse import observe
from openai import OpenAI

from mcr_generation.app.configs.settings import LLMConfig
from mcr_generation.app.schemas.base import NarrativeSynthesis
from mcr_generation.app.schemas.celery_types import ReportTypes
from mcr_generation.app.services.sections.narrative.prompts import (
    NARRATIVE_PROMPT_TEMPLATE,
)
from mcr_generation.app.services.sections.narrative.types import NarrativeChunk
from mcr_generation.app.services.utils.input_chunker import Chunk
from mcr_generation.app.services.utils.llm_helpers import (
    call_llm_with_structured_output,
)


class NarrativeSynthesisGenerator:
    """Générateur de la synthèse narrative (NARRATIVE_SYNTHESIS).

    Générateur autonome (comme ``CustomReportGenerator``) : il ne dérive pas de
    ``BaseReportGenerator`` car sa sortie est un texte narratif libre
    (``NarrativeSynthesis``), pas un rapport structuré (``BaseReport``).

    Reformule chaque chunk de transcription en discours indirect
    (« X a dit que Y »), dans l'ordre chronologique, puis concatène les
    reformulations en un seul texte narratif libre (pas de sections structurées,
    pas de header).
    """

    report_type: ClassVar[ReportTypes] = ReportTypes.NARRATIVE_SYNTHESIS

    def __init__(self) -> None:
        self.llm_config = LLMConfig()
        self.client_instructor = instructor.from_openai(
            OpenAI(
                base_url=self.llm_config.LLM_HUB_API_URL,
                api_key=self.llm_config.LLM_HUB_API_KEY,
            ),
            mode=instructor.Mode.JSON,
        )

    @observe(name="generate_narrative_synthesis")
    def generate(
        self,
        chunks: list[Chunk],
        notes_content: str | None = None,
    ) -> NarrativeSynthesis:
        """Reformule chaque chunk en discours indirect et concatène le résultat."""
        narratives: list[str] = []
        for chunk in chunks:
            user_message_content = NARRATIVE_PROMPT_TEMPLATE.format(
                chunk_text=chunk.text,
                speaker_mapping="Non fourni",
            )
            result = call_llm_with_structured_output(
                client=self.client_instructor,
                response_model=NarrativeChunk,
                user_message_content=user_message_content,
            )
            narratives.append(result.narrative)

        return NarrativeSynthesis(narrative="\n\n".join(narratives))
