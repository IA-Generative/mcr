from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PgSettings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(
        from_attributes=True, case_sensitive=True, env_file=".env", extra="allow"
    )


class LoggingSettings(BaseSettings):
    COLORIZE: bool = Field(default=False, description="Should log output be colored")
    LEVEL: int | str = Field(default="INFO")
    DISPLAY_TIMESTAMP: bool = Field(
        default=False, description="Should display log timestamp"
    )


class S3Settings(BaseSettings):
    S3_ENDPOINT: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET: str
    S3_REGION: str
    S3_AUDIO_FOLDER: str = "audio"
    S3_TRACE_FOLDER: str = "trace"

    model_config = SettingsConfigDict(
        from_attributes=True, case_sensitive=True, env_file=".env", extra="allow"
    )


class CaptureSettings(BaseSettings):
    BROWSER_HEADLESS: bool = True
    MAX_RETRIES: int = Field(
        30,
        description="Number of try to manually locate an element via a playwright locator before giving up",
    )
    RETRY_DELAY: int = Field(
        1,
        description="Time in seconds before manually retrying to locate an element via a playwright locator",
    )
    TIMEOUT_INDIVIDUAL_BOT_ACTION_MS: int = Field(
        10_000,
        description="Time in ms before a playwright action raise a TimeoutError when trying an action",
    )

    model_config = SettingsConfigDict(
        from_attributes=True, case_sensitive=True, env_file=".env", extra="allow"
    )


class ApiSettings(BaseSettings):
    CORE_SERVICE_BASE_URL: str

    @property
    def MEETING_PREFIX(self) -> str:
        return f"{self.CORE_SERVICE_BASE_URL}/api/meetings"
