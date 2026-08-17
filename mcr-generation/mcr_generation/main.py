from celery.worker import WorkController

import mcr_generation.app.services.report_generation_task_service  # noqa: F401
from mcr_generation.app.configs.settings import LLMConfig
from mcr_generation.app.utils.celery_worker import celery_app
from mcr_generation.app.utils.langfuse_observability import init_langfuse
from mcr_generation.setup.logger import setup_logging

llm_config = LLMConfig()
setup_logging()

init_langfuse()


def start_worker() -> None:
    w = WorkController(app=celery_app)  # type: ignore[call-arg]
    w.start()  # type: ignore


if __name__ == "__main__":
    start_worker()
