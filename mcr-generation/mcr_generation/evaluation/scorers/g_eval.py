"""G-Eval scorer: drives the LLM-judge from a `Criterion`'s prompt template."""

import instructor
from instructor import Instructor
from loguru import logger
from openai import OpenAI
from pydantic import BaseModel, Field

from mcr_generation.app.configs.settings import LLMConfig
from mcr_generation.app.services.utils.llm_helpers import (
    call_llm_with_structured_output,
)
from mcr_generation.evaluation.pipeline.types import Criterion, ScoreResult


class _JudgeResponse(BaseModel):
    score: int = Field(description="Score on the 1-5 scale defined in the prompt.")
    justification: str = Field(
        description="One- or two-sentence justification for the score."
    )


class GEvalScorer:
    """Calls the configured LLM to score a single criterion."""

    def __init__(self, client: Instructor | None = None) -> None:
        self._llm_config = LLMConfig()
        self._client = client or instructor.from_openai(
            OpenAI(
                base_url=self._llm_config.LLM_HUB_API_URL,
                api_key=self._llm_config.LLM_HUB_API_KEY,
            ),
            mode=instructor.Mode.JSON,
        )

    def score(
        self,
        criterion: Criterion,
        report: str,
        reference: str | None,
    ) -> ScoreResult:
        prompt = criterion.render(report=report, reference=reference)
        try:
            response = call_llm_with_structured_output(
                client=self._client,
                response_model=_JudgeResponse,
                user_message_content=prompt,
            )
        except Exception as exc:
            logger.opt(exception=exc).warning(
                "G-Eval scoring failed for criterion {}", criterion.name
            )
            return ScoreResult(value=None, justification=f"LLM call failed: {exc}")

        low, high = criterion.scale
        if response.score < low or response.score > high:
            logger.warning(
                "Criterion {} returned out-of-scale score {} (expected {}-{})",
                criterion.name,
                response.score,
                low,
                high,
            )
            return ScoreResult(
                value=None,
                justification=(
                    f"Out-of-scale score {response.score}; raw justification: "
                    f"{response.justification}"
                ),
            )
        return ScoreResult(value=response.score, justification=response.justification)
