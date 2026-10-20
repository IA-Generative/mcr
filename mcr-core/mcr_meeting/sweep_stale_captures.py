from loguru import logger

from mcr_meeting.app.db.db import worker_db_session_context_manager
from mcr_meeting.app.infrastructure.logger import setup_logging
from mcr_meeting.app.use_cases.fail_stale_captures import fail_stale_captures
from mcr_meeting.app.use_cases.fail_stale_transcriptions import (
    fail_stale_transcriptions,
)


def main() -> None:
    setup_logging()
    with worker_db_session_context_manager():
        captures = fail_stale_captures()
        transcriptions = fail_stale_transcriptions()
    logger.info(
        "Stale sweep done: {} capture(s) and {} transcription(s) failed",
        len(captures),
        len(transcriptions),
    )


if __name__ == "__main__":
    main()
