from celery.worker import WorkController
from langfuse import Langfuse

import mcr_generation.app.services.report_generation_task_service  # noqa: F401
from mcr_generation.app.configs.settings import LangfuseSettings, LLMConfig
from mcr_generation.app.utils.celery_worker import celery_app
from mcr_generation.setup.logger import setup_logging

llm_config = LLMConfig()
setup_logging()

langfuse_settings = LangfuseSettings()

# N.B: Need to initialize Langfuse client to capture observations within Celery tasks
Langfuse(
    secret_key=langfuse_settings.LANGFUSE_SECRET_KEY,
    public_key=langfuse_settings.LANGFUSE_PUBLIC_KEY,
    host=langfuse_settings.LANGFUSE_HOST,
    environment=langfuse_settings.ENV_MODE.lower(),  # only lowercase supported
)


def start_worker() -> None:
    w = WorkController(app=celery_app)  # type: ignore[call-arg]
    w.start()  # type: ignore


if __name__ == "__main__":
    start_worker()
