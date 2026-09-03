from loguru import logger

from mcr_meeting.app.db.db import worker_db_session_context_manager
from mcr_meeting.app.infrastructure.logger import setup_logging
from mcr_meeting.app.use_cases.fail_stale_captures import fail_stale_captures


def main() -> None:
    setup_logging()
    with worker_db_session_context_manager():
        failed = fail_stale_captures()
    logger.info("Stale capture sweep done: {} meeting(s) failed", len(failed))


if __name__ == "__main__":
    main()
