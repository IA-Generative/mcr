from langchain.prompts import PromptTemplate
from langfuse import observe
from openai import AsyncOpenAI

from mcr_generation.app.configs.settings import LLMConfig
from mcr_generation.app.schemas.custom_prompt import RewriterOutput
from mcr_generation.app.services.metadata_collectors import METADATA_COLLECTORS
from mcr_generation.app.services.rewriter.prompts import REWRITER_PROMPT_TEMPLATE
from mcr_generation.app.services.utils.llm_helpers import (
    async_call_llm_with_structured_output,
)


def _format_collectors_doc() -> str:
    return "\n".join(
        f"   - `{cid}` : {collector.description}"
        for cid, collector in METADATA_COLLECTORS.items()
    )


class Rewriter:
    def __init__(self) -> None:
        self.llm_config = LLMConfig()
        self.llm_client = AsyncOpenAI(
            base_url=self.llm_config.LLM_API_BASE_URL,
            api_key=self.llm_config.LLM_API_KEY,
            timeout=self.llm_config.LLM_API_TIMEOUT,
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
        return await async_call_llm_with_structured_output(
            client=self.llm_client,
            response_model=RewriterOutput,
            user_message_content=message,
        )
