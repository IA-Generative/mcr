import instructor
from langchain.prompts import PromptTemplate
from langfuse import observe
from loguru import logger
from openai import AsyncOpenAI

from mcr_generation.app.configs.settings import LLMConfig
from mcr_generation.app.schemas.custom_prompt import RewriterOutput, SectionSpec
from mcr_generation.app.services.metadata_collectors import METADATA_COLLECTORS
from mcr_generation.app.services.rewriter.prompts import REWRITER_PROMPT_TEMPLATE


def _format_collectors_doc() -> str:
    lines = []
    for cid, collector in METADATA_COLLECTORS.items():
        lines.append(f"   - `{cid}` : {collector.description}")
    return "\n".join(lines)


class Rewriter:
    def __init__(self) -> None:
        self.llm_config = LLMConfig()
        self.client = instructor.from_openai(
            AsyncOpenAI(
                base_url=self.llm_config.LLM_HUB_API_URL,
                api_key=self.llm_config.LLM_HUB_API_KEY,
            ),
            mode=instructor.Mode.JSON,
        )

    @observe(name="rewriter")
    async def rewrite(self, raw_prompt: str) -> RewriterOutput:
        message = (
            PromptTemplate(
                template=REWRITER_PROMPT_TEMPLATE,
                input_variables=["raw_prompt", "collectors_doc"],
            )
            .invoke(
                {
                    "raw_prompt": raw_prompt,
                    "collectors_doc": _format_collectors_doc(),
                }
            )
            .to_string()
        )

        raw_output: RewriterOutput = await self.client.chat.completions.create(
            model=self.llm_config.LLM_MODEL_NAME,
            response_model=RewriterOutput,
            temperature=self.llm_config.TEMPERATURE,
            messages=[{"role": "user", "content": message}],
        )

        return _sanitize(raw_output)


def _sanitize(out: RewriterOutput) -> RewriterOutput:
    """Fallback unknown collector_ids to generic instructions, log warnings."""
    valid_ids = set(METADATA_COLLECTORS.keys())
    sanitized: list[SectionSpec] = []
    for spec in out.sections:
        if spec.collector_id is not None and spec.collector_id not in valid_ids:
            logger.warning(
                "Rewriter returned unknown collector_id={!r}, falling back to generic.",
                spec.collector_id,
            )
            sanitized.append(
                SectionSpec(
                    heading=spec.heading,
                    collector_id=None,
                    instruction=spec.instruction or spec.heading,
                )
            )
        else:
            sanitized.append(spec)
    return RewriterOutput(title=out.title, sections=sanitized)
