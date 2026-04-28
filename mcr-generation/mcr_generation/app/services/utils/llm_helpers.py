from typing import TypeVar

from instructor import Instructor
from langfuse import get_client, observe
from pydantic import BaseModel
from tenacity import Retrying, stop_after_attempt, wait_exponential

from mcr_generation.app.configs.settings import LLMConfig
from mcr_generation.app.exceptions.exceptions import LLMCallError

llm_config = LLMConfig()

T = TypeVar("T", bound=BaseModel)


@observe(as_type="generation", capture_input=False)
def call_llm_with_structured_output(
    client: Instructor,
    response_model: type[T],
    user_message_content: str,
    model_name: str = llm_config.LLM_MODEL_NAME,
    temperature: float = llm_config.TEMPERATURE,
    max_retry_attempts: int = llm_config.RETRY_MAX_ATTEMPTS,
    retry_wait_multiplier: int = llm_config.RETRY_WAIT_MULTIPLIER,
    retry_min_wait: float = llm_config.RETRY_MIN_WAIT_TIME,
    retry_max_wait: float = llm_config.RETRY_MAX_WAIT_TIME,
) -> T:
    langfuse = get_client()
    langfuse.update_current_generation(
        model=model_name,
        input=[{"role": "user", "content": user_message_content}],
        model_parameters={"temperature": str(temperature)},
        metadata={
            "response_model": response_model.__name__,
            "max_retry_attempts": max_retry_attempts,
            "retry_wait_multiplier": retry_wait_multiplier,
            "retry_min_wait": retry_min_wait,
            "retry_max_wait": retry_max_wait,
        },
    )
    try:
        response: T = client.chat.completions.create(
            model=model_name,
            response_model=response_model,
            temperature=temperature,
            messages=[{"role": "user", "content": user_message_content}],
            max_retries=Retrying(
                stop=stop_after_attempt(max_retry_attempts),
                wait=wait_exponential(
                    multiplier=retry_wait_multiplier,
                    min=retry_min_wait,
                    max=retry_max_wait,
                ),
            ),
        )
    except Exception as e:
        raise LLMCallError(f"LLM call failed for {response_model.__name__}: {e}") from e

    raw = getattr(response, "_raw_response", None)
    usage = getattr(raw, "usage", None)
    if usage is not None:
        langfuse.update_current_generation(
            usage_details={
                "input": usage.prompt_tokens,
                "output": usage.completion_tokens,
                "total": usage.total_tokens,
            }
        )
    return response
