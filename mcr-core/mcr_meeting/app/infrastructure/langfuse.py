from langfuse import Langfuse, get_client
from loguru import logger

from mcr_meeting.app.configs.base import LangfuseSettings, Settings


def init_langfuse() -> None:
    langfuse_settings = LangfuseSettings()
    settings = Settings()
    client = None
    authenticated = False
    try:
        client = Langfuse(
            secret_key=langfuse_settings.LANGFUSE_SECRET_KEY,
            public_key=langfuse_settings.LANGFUSE_PUBLIC_KEY,
            host=langfuse_settings.LANGFUSE_HOST,
            environment=settings.ENV_MODE.lower(),
        )
        authenticated = client.auth_check()
        if not authenticated:
            logger.warning("Langfuse authentication failed, tracing disabled")
    except Exception as e:
        logger.warning("Langfuse initialization failed, tracing disabled: {}", e)

    if not authenticated and client is not None:
        try:
            client.shutdown()
        except Exception as e:
            logger.warning("Langfuse shutdown failed: {}", e)


def record_participant_name_lost_event(
    speaker_id: str,
    step_index: int,
    previous_name: str,
    reason: str,
) -> None:
    try:
        get_client().create_event(
            name="participant_name_lost",
            level="WARNING",
            metadata={
                "speaker_id": speaker_id,
                "step_index": step_index,
                "previous_name": previous_name,
                "reason": reason,
            },
        )
    except Exception as e:
        logger.warning("langfuse create_event (participant_name_lost) failed: {}", e)
