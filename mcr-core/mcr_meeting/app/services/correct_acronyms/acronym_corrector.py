from mcr_meeting.app.services.correct_acronyms.prompt import (
    ACRONYM_PROMPT_TEMPLATE,
    GLOSSARY_CONTENT,
)
from mcr_meeting.app.services.correct_spelling_mistakes.spelling_corrector import (
    CorrectedText,
    SpellingCorrector,
)
from mcr_meeting.app.services.llm_post_processing import Chunk


class AcronymCorrector(SpellingCorrector):
    def __init__(self) -> None:
        super().__init__()
        self._prompt_template = ACRONYM_PROMPT_TEMPLATE.format(
            glossary=GLOSSARY_CONTENT,
            text="{text}",
        )

    def _correct_chunk(self, chunk: Chunk) -> str:
        result = self.client.chat.completions.create(
            model=self.settings.LLM_MODEL_NAME,
            response_model=CorrectedText,
            messages=[
                {
                    "role": "user",
                    "content": self._prompt_template.format(text=chunk.text),
                }
            ],
        )
        return result.corrected_text
