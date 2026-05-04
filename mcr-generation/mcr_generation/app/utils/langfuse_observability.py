from langfuse import get_client
from loguru import logger


def record_report_trace_context(
    meeting_id: int,
    transcription_object_filename: str,
    report_type: str,
    env_mode: str,
) -> None:
    try:
        get_client().update_current_trace(
            session_id=str(meeting_id),
            tags=[
                f"env:{env_mode.lower()}",
                f"report_type:{report_type}",
                "pipeline:generation",
            ],
            metadata={
                "transcription_object": transcription_object_filename,
            },
            input={
                "meeting_id": meeting_id,
                "transcription_object": transcription_object_filename,
                "report_type": report_type,
            },
        )
    except Exception as e:
        logger.warning("langfuse update_current_trace (context) failed: {}", e)


def record_chunking_metadata(chunk_count: int, total_chars: int) -> None:
    try:
        get_client().update_current_trace(
            metadata={
                "chunk_count": chunk_count,
                "total_chars": total_chars,
            },
        )
    except Exception as e:
        logger.warning("langfuse update_current_trace (chunking) failed: {}", e)


def record_generation_input(
    response_model_name: str,
    user_message_content: str,
    model_name: str,
    temperature: float,
    max_retry_attempts: int,
    retry_wait_multiplier: int,
    retry_min_wait: float,
    retry_max_wait: float,
) -> None:
    try:
        get_client().update_current_generation(
            model=model_name,
            input=[{"role": "user", "content": user_message_content}],
            # Langfuse types model_parameters values as str | int | bool | None
            # → float must be cast to str.
            model_parameters={"temperature": str(temperature)},
            metadata={
                "response_model": response_model_name,
                "max_retry_attempts": max_retry_attempts,
                "retry_wait_multiplier": retry_wait_multiplier,
                "retry_min_wait": retry_min_wait,
                "retry_max_wait": retry_max_wait,
            },
        )
    except Exception as e:
        logger.warning("langfuse update_current_generation (input) failed: {}", e)


def record_generation_usage(
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
) -> None:
    try:
        get_client().update_current_generation(
            usage_details={
                "input": prompt_tokens,
                "output": completion_tokens,
                "total": total_tokens,
            }
        )
    except Exception as e:
        logger.warning("langfuse update_current_generation (usage) failed: {}", e)
