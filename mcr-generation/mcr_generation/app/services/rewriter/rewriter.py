import instructor
from langchain.prompts import PromptTemplate
from langfuse import observe
from openai import AsyncOpenAI

from mcr_generation.app.configs.settings import LLMConfig
from mcr_generation.app.exceptions.exceptions import LLMCallError
from mcr_generation.app.schemas.custom_prompt import RewriterOutput
from mcr_generation.app.services.metadata_collectors import METADATA_COLLECTORS
from mcr_generation.app.services.rewriter.prompts import REWRITER_PROMPT_TEMPLATE


def _format_collectors_doc() -> str:
    return "\n".join(
        f"   - `{cid}` : {collector.description}"
        for cid, collector in METADATA_COLLECTORS.items()
    )


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
        try:
            output: RewriterOutput = await self.client.chat.completions.create(
                model=self.llm_config.LLM_MODEL_NAME,
                response_model=RewriterOutput,
                temperature=self.llm_config.TEMPERATURE,
                messages=[{"role": "user", "content": message}],
            )
        except Exception as e:
            raise LLMCallError(f"Rewriter LLM call failed: {e}") from e
        return output
