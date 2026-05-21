from langfuse import get_client
from loguru import logger


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
