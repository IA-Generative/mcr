from typing import Any

import sentry_sdk
from celery import Celery
from celery.signals import task_postrun, worker_shutdown
from langfuse import get_client
from sentry_sdk.integrations.celery import CeleryIntegration

from mcr_generation.app.configs.settings import CelerySettings, SentrySettings
from mcr_generation.app.schemas.celery_types import MCRReportGenerationTasks

sentrySettings = SentrySettings()

sentry_sdk.init(
    dsn=sentrySettings.SENTRY_GENERATION_DSN,
    send_default_pii=sentrySettings.SEND_DEFAULT_PII,
    traces_sample_rate=sentrySettings.TRACES_SAMPLE_RATE,
    environment=sentrySettings.ENV_MODE,
    ignore_errors=[],
    integrations=[CeleryIntegration()],
)

celerySettings = CelerySettings()

celery_app = Celery(
    broker=celerySettings.CELERY_BROKER_URL,
)

celery_app.conf.task_track_started = True
celery_app.conf.result_expires = 3600
celery_app.conf.task_default_queue = MCRReportGenerationTasks.BASE_NAME
celery_app.conf.loglevel = "WARNING"


celery_app.conf.task_acks_late = True


@task_postrun.connect
def _flush_langfuse_after_task(**_: Any) -> None:
    get_client().flush()


@worker_shutdown.connect
def _shutdown_langfuse(**_: Any) -> None:
    get_client().shutdown()
