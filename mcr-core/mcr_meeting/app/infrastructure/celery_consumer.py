from typing import Any

import celery.app.trace  # type: ignore[import-untyped]
from celery import Celery, Task
from celery.signals import setup_logging as celery_setup_logging

from mcr_meeting.app.configs.base import CelerySettings
from mcr_meeting.app.schemas.celery_types import MCRTranscriptionTasks
from mcr_meeting.setup.logger import setup_logging

setup_logging()


@celery_setup_logging.connect
def _configure_celery_logging(**_: Any) -> None:  # type: ignore[explicit-any]
    # Connecting any receiver tells Celery to skip its own logging setup
    # (which would install [LEVEL/Worker-N] handlers). setup_logging() already
    # ran at module import — nothing to do here.
    pass


# Drop %(return_value)s from Celery's success log: the transcribe task returns
# the full transcription, which would dump thousands of chars per task.
celery.app.trace.LOG_SUCCESS = "Task %(name)s[%(id)s] succeeded in %(runtime)ss"


celery_settings = CelerySettings()

celery_worker = Celery(
    "transcriber",
    broker=celery_settings.CELERY_BROKER_URL,
    backend=celery_settings.CELERY_BACKEND_URL,
)

celery_worker.conf.task_track_started = True
celery_worker.conf.result_expires = 3600
celery_worker.conf.task_default_queue = MCRTranscriptionTasks.BASE_NAME
celery_worker.conf.worker_concurrency = 1
celery_worker.conf.worker_prefetch_multiplier = 1
celery_worker.conf.task_acks_late = True
celery_worker.conf.worker_soft_shutdown_timeout = (
    celery_settings.WORKER_SOFT_SHUTDOWN_TIMEOUT_SECONDS
)
celery_worker.conf.broker_transport_options = {
    "visibility_timeout": celery_settings.REDIS_VISIBILITY_TIMEOUT,
    # Transcriptions run for a long time, so this worker needs a long
    # visibility_timeout. Kombu's Redis transport restores (redelivers) unacked
    # messages by scanning a broker-global "unacked index" with no queue filter,
    # using each consumer's own visibility_timeout as the cutoff. Any other Celery
    # app on this Redis DB with a shorter timeout would therefore redeliver our
    # still-running tasks, causing duplicate transcriptions. Dedicated unacked keys
    # scope this worker's restore bookkeeping to its own messages only.
    "unacked_key": "unacked_transcription",
    "unacked_index_key": "unacked_index_transcription",
    "unacked_mutex_key": "unacked_mutex_transcription",
}


class MeetingPipelineTask(Task[Any, Any]):  # type: ignore[explicit-any]
    def set_task_context(self, meeting_id: int, owner_keycloak_uuid: str) -> None:
        raise NotImplementedError

    def before_start(  # type: ignore[explicit-any]
        self, task_id: str, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> None:
        self.set_task_context(args[0], args[1])
