from typing import Type, TypeVar

from instructor import Instructor
from langfuse import observe
from pydantic import BaseModel
from tenacity import Retrying, stop_after_attempt, wait_exponential

from mcr_generation.app.configs.settings import LLMConfig

llm_config = LLMConfig()

T = TypeVar("T", bound=BaseModel)


@observe(as_type="generation")
def call_llm_with_structured_output(
    client: Instructor,
    response_model: Type[T],
    user_message_content: str,
    model_name: str = llm_config.LLM_MODEL_NAME,
    temperature: float = llm_config.TEMPERATURE,
    max_retry_attempts: int = llm_config.RETRY_MAX_ATTEMPTS,
    retry_wait_multiplier: int = llm_config.RETRY_WAIT_MULTIPLIER,
    retry_min_wait: float = llm_config.RETRY_MIN_WAIT_TIME,
    retry_max_wait: float = llm_config.RETRY_MAX_WAIT_TIME,
) -> T:
    response: T = client.chat.completions.create(
        model=model_name,
        response_model=response_model,
        temperature=temperature,
        messages=[{"role": "user", "content": user_message_content}],
        max_retries=Retrying(
            stop=stop_after_attempt(max_retry_attempts),
            wait=wait_exponential(
                multiplier=retry_wait_multiplier, min=retry_min_wait, max=retry_max_wait
            ),
        ),
    )
    return response
