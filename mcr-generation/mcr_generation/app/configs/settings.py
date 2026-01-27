"""
Settings of MCR Generation
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

ALLOWED_ENVIRONMENTS = ["test", "DEV", "DATA", "STAGING", "PREPROD", "PROD"]


class EnvBaseSettings(BaseSettings):
    """
    Base settings class to define common configurations
    """

    ENV_MODE: str = Field(description="Environment mode", default="DEV")

    @field_validator("ENV_MODE")
    def validate_env_mode(cls, v: str) -> str:
        if v not in ALLOWED_ENVIRONMENTS:
            raise ValueError(f"Invalid environment mode: {v}")
        return v


class LoggingSettings(BaseSettings):
    COLORIZE: bool = Field(default=False, description="Should log output be colored")
    LEVEL: int | str = Field(default="INFO")
    DISPLAY_TIMESTAMP: bool = Field(
        default=False, description="Should display log timestamp"
    )


class LLMConfig(BaseSettings):
    """
    Settings parameters for calling an API hosted LLM
    """

    LLM_HUB_API_URL: str = Field(
        ...,
        description="llm hub endpoint serving the llm",
    )
    LLM_HUB_API_KEY: str = Field(..., description="llm hub api key")

    LLM_MODEL_NAME: str = Field(
        default="mistral-small-24b", description="large language model"
    )
    TEMPERATURE: float = Field(
        default=0,
        ge=0.0,
        le=1.0,
        description="LLM sampling temperature (0-1). Lower values (0) produce deterministic, focused outputs. Higher values (0.7-1) increase creativity and randomness.",
    )
    RETRY_MAX_ATTEMPTS: int = Field(
        default=5, description="Maximum number of retry attempts for LLM API calls"
    )
    RETRY_WAIT_MULTIPLIER: int = Field(
        default=5, description="Exponential backoff multiplier for retry wait times"
    )
    RETRY_MIN_WAIT_TIME: float = Field(
        default=2, description="Minimum wait time in seconds between retries"
    )
    RETRY_MAX_WAIT_TIME: float = Field(
        default=100, description="Maximum wait time in seconds between retries"
    )


class LangfuseSettings(EnvBaseSettings):
    """
    Settings parameters for Langfuse monitoring
    """

    LANGFUSE_PUBLIC_KEY: str = Field(description="Langfuse public key")
    LANGFUSE_SECRET_KEY: str = Field(description="Langfuse secret key")
    LANGFUSE_HOST: str = Field(description="Langfuse host URL")


class ChunkingConfig(BaseSettings):
    """
    Settings of the chunking process
    """

    CHUNK_SIZE: int = Field(
        default=20000, description="Maximum number of character of per chunk"
    )
    CHUNK_OVERLAP: int = Field(
        default=100, description="Nb of overleaping characters between chunks"
    )


class CelerySettings(BaseSettings):
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_VHOST_TASK_DB: int = 0
    REDIS_VHOST_RESULT_DB: int = 1

    @property
    def CELERY_BROKER_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_VHOST_TASK_DB}"

    @property
    def CELERY_BACKEND_URL(self) -> str:
        return (
            f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_VHOST_RESULT_DB}"
        )


class S3Settings(BaseSettings):
    """
    Configuration settings for the S3 bucket
    """

    S3_ENDPOINT: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET: str = Field(
        default="mcr",
        description="The name of the S3 bucket where files are stored.",
    )
    S3_REGION: str


class ApiSettings(BaseSettings):
    CORE_SERVICE_BASE_URL: str

    @property
    def MCR_CORE_API_URL(self) -> str:
        return f"{self.CORE_SERVICE_BASE_URL}/api"


class SentrySettings(EnvBaseSettings):
    """
    Configuration settings for Sentry
    """

    SENTRY_GENERATION_DSN: str = Field(description="Sentry DSN for core service")
    SEND_DEFAULT_PII: bool = Field(default=True, description="Send default PII")
    TRACES_SAMPLE_RATE: float = Field(
        default=0.2, description="Sentry traces sample rate"
    )
