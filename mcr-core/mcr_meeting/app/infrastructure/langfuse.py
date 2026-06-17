from langfuse import Langfuse

from mcr_meeting.app.configs.base import LangfuseSettings, Settings


def init_langfuse() -> None:
    langfuse_settings = LangfuseSettings()
    settings = Settings()
    Langfuse(
        secret_key=langfuse_settings.LANGFUSE_SECRET_KEY,
        public_key=langfuse_settings.LANGFUSE_PUBLIC_KEY,
        host=langfuse_settings.LANGFUSE_HOST,
        environment=settings.ENV_MODE.lower(),
    )
