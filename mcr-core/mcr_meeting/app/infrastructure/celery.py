from celery import Celery

from mcr_meeting.app.configs.base import CelerySettings
from mcr_meeting.app.schemas.celery_types import (
    MCRReportGenerationTasks,
    MCRTranscriptionTasks,
)

celery_settings = CelerySettings()

celery_producer_app = Celery(
    broker=celery_settings.CELERY_BROKER_URL,
)

celery_producer_app.conf.task_routes = {
    MCRTranscriptionTasks.select_all_tasks(): {
        "queue": MCRTranscriptionTasks.BASE_NAME
    },
    MCRReportGenerationTasks.select_all_tasks(): {
        "queue": MCRReportGenerationTasks.BASE_NAME
    },
}
