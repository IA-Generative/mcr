"""Base settings class contains only important fields."""

from typing import Optional

from openai import NotGiven
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ALLOWED_ENVIRONMENTS = ["test", "DEV", "DATA", "STAGING", "PREPROD", "PROD"]


class DBSettings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    DEBUG: bool = False


class ServiceSettings(BaseSettings):
    CORE_SERVICE_BASE_URL: str


class Settings(BaseSettings):
    PROJECT_SLUG: str = "mcr_meeting"
    MCR_FRONTEND_URL: str
    DEBUG: bool = False
    ENV_MODE: str = Field(description="Environment mode")

    @field_validator("ENV_MODE")
    def validate_env_mode(cls, v: str) -> str:
        if v not in ALLOWED_ENVIRONMENTS:
            raise ValueError(f"Invalid environment mode: {v}")
        return v


class LoggingSettings(BaseSettings):
    COLORIZE: bool = Field(default=False, description="Should log output be colored")
    LEVEL: int | str = Field(default="INFO")
    DISPLAY_REQUEST_ID: bool = Field(
        default=True, description="Should display request id in logs"
    )
    DISPLAY_TIMESTAMP: bool = Field(
        default=False, description="Should display log timestamp"
    )


class AudioSettings(BaseSettings):
    """
    Configuration settings for audio and transcription processing
    """

    SAMPLE_RATE: int = Field(
        16000,
        description="""Target audio sample rate in Hz. 16000 Hz is standard for speech-to-text.
                It captures human speech clearly while optimizing model performance and size.""",
    )

    NB_AUDIO_CHANNELS: int = Field(
        1,
        description="Mono (1 channel) is standard for speech-to-text, ensuring consistent input and reducing computational load.",
    )

    NO_SPEECH_PROB_THRESHOLD: float = Field(
        0.6,
        description="""non speech probability threshold. we exclude segment 
                       with non speech probability higher than this value """,
    )


class VADSettings(BaseSettings):
    """
    Configuration settings for Voice Activity Detection (VAD)
    """

    VAD_MODEL: str = Field(
        default="pyannote/voice-activity-detection",
        description="Pretrained model name for voice activity detection.",
    )
    MIN_SPEECH_DURATION: float = Field(
        default=0.35,
        description="Minimum duration (in seconds) for a speech segment to be considered valid.",
    )
    MAX_SILENCE_GAP: float = Field(
        default=0.3,
        description="Maximum allowed gap of silence (in seconds) between speech segments to merge them (natural speech short pause between two spans belonging to the same sentence.).",
    )
    MIN_TOTAL_VOICED_DURATION: float = Field(
        default=0.5,
        description="Minimum total duration (in seconds) of voiced segments required to consider the audio as containing speech.",
    )


class PyannoteDiarizationParameters(BaseSettings):
    """
    Configuration settings for Pyannote Speaker Diarization
    """

    min_duration_off: float = Field(
        default=1.5,
        description="Minimum duration of silence (in seconds) to consider a speaker change.",
    )
    threshold: float = Field(
        default=0.65,
        description="Clustering threshold for speaker diarization. Lower values result in more speakers being identified, while higher values merge similar speakers together.",
    )
    min_cluster_size: int = Field(
        default=12,
        description="Minimum number of speech segments required to form a speaker cluster.",
    )


class WhisperTranscriptionSettings(BaseSettings):
    """
    Configuration settings for Whisper Transcription
    """

    LANGUAGE: Optional[str] = Field(
        default="fr",
        description="The language of the audio. If None, language detection will be performed.",
    )
    WORD_TIMESTAMPS: Optional[bool] = Field(
        default=True,
        description="For the model to return word_timestamps or just segment timestamps.",
    )
    INITIAL_PROMPT: str | NotGiven = Field(
        default="Ceci est la transcription d'une réunion d'équipe avec plusieurs intervenants ; reformule le texte dans un langage naturel et fluide, sans répétitions.",
        description="Prompt passed to the transcription model",
    )


class Speech2TextSettings(BaseSettings):
    """
    Configuration settings parameters for speech to text transcription
    """

    HUGGINGFACE_API_KEY: str = Field(
        default="", description="Hugging Face API key for accessing gated models."
    )
    STT_MODEL: str = Field(
        default="large-v3-turbo", description="speech to text model name"
    )
    DIARIZATION_MODEL: str = Field(
        default="pyannote/speaker-diarization-3.1",
        description="model name for speaker diarization.",
    )
    NOISE_FILTERS: str = "highpass=f=80,afftdn=nf=-25,agate=threshold=0.015:ratio=2,equalizer=f=250:width_type=h:width=200:g=-2,equalizer=f=3500:width_type=h:width=2500:g=3,acompressor=threshold=-18dB:ratio=2.5:attack=15:release=200:makeup=1,loudnorm=I=-18:LRA=6:TP=-1.5"  # TODO: Change noise filter


class TranscriptionWaitingTimeSettings(BaseSettings):
    """
    Configuration settings for transcription waiting time
    """

    model_config = SettingsConfigDict(case_sensitive=True)

    PARALLEL_PODS_COUNT: int = Field(
        default=14,
        description="The number of transcription pods in parallel.",
    )
    AVERAGE_TRANSCRIPTION_TIME_MINUTES: int = Field(
        default=12,
        description="The average transcription time in minutes.",
    )

    AVERAGE_TRANSCRIPTION_SPEED: int = Field(
        default=5,
        description="The average ratio between real audio time to transcription time.",
    )

    AVERAGE_MEETING_DURATION_HOURS: float = Field(
        default=1,
        description="The average meeting duration in hours.",
    )


class S3Settings(BaseSettings):
    """
    Configuration settings for the S3 bucket
    """

    model_config = SettingsConfigDict(case_sensitive=True)

    # ########################### S3 Configuration ###########################
    S3_ENDPOINT: str
    S3_EXTERNAL_ENDPOINT: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET: str = Field(
        default="mcr",
        description="The name of the S3 bucket where files are stored.",
    )
    S3_REGION: str
    S3_EVALUATION_FOLDER: str = Field(
        default="evaluation",
        description="The folder in the S3 bucket where evaluation files are stored.",
    )
    S3_TRANSCRIPTION_FOLDER: str = Field(
        default="transcription",
        description="The folder in the S3 bucket where transcription files are stored.",
    )
    S3_REPORT_FOLDER: str = Field(
        default="report",
        description="The folder in the S3 bucket where report files are stored.",
    )
    S3_AUDIO_FOLDER: str = Field(
        default="audio",
        description="The folder in the S3 bucket where audio files are stored.",
    )


class ApiSettings(BaseSettings):
    """
    Configuration settings for the API
    """

    model_config = SettingsConfigDict(case_sensitive=True)

    # ########################### API Prefixes ###########################
    USER_API_PREFIX: str = "/api/user"
    FEATURE_FLAG_API_PREFIX: str = "/api/feature-flag"
    MEETING_API_PREFIX: str = "/api/meetings"
    TRANSCRIPTION_API_PREFIX: str = "/api/transcription"


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


class SMTPSettings(BaseSettings):
    """
    Configuration settings for SMTP email service
    """

    model_config = SettingsConfigDict(case_sensitive=True)

    SMTP_USERNAME: str = Field(description="SMTP username for authentication")
    SMTP_SENDER: str = Field(description="Email address to send from")
    SMTP_ENDPOINT: str = Field(description="SMTP server endpoint")
    SMTP_PORT: int = Field(default=465, description="SMTP server port")
    SMTP_DEFAULT_PORT: int = Field(default=25, description="Default SMTP port")
    SMTP_SECRET: str = Field(description="SMTP password/secret for authentication")


class UnleashSettings(BaseSettings):
    """
    Configuration settings for Unleash feature flags (Gitlab Feature Flags is compatible with Unleash API)
    """

    model_config = SettingsConfigDict(case_sensitive=True)

    UNLEASH_URL: str = Field(description="Unleash server URL")
    UNLEASH_INSTANCE_ID: str = Field(
        description="Instance ID for Unleash authentication"
    )


class SentrySettings(BaseSettings):
    """
    Configuration settings for Sentry
    """

    model_config = SettingsConfigDict(case_sensitive=True)

    SENTRY_CORE_DSN: str = Field(description="Sentry DSN for core service")
    SENTRY_TRANSCRIPTION_DSN: str = Field(
        description="Sentry DSN for transcription service"
    )
    SEND_DEFAULT_PII: bool = Field(default=True, description="Send default PII")
    TRACES_SAMPLE_RATE: float = Field(default=0.2, description="Traces sample rate")


class LLMSettings(BaseSettings):
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


class TranscriptionApiSettings(BaseSettings):
    """
    Configuration settings for API-based transcription and diarization services
    """

    model_config = SettingsConfigDict(case_sensitive=True)

    # Transcription API (OpenAI-compatible)
    TRANSCRIPTION_API_BASE_URL: str = Field(
        description="Base URL for OpenAI-compatible transcription API"
    )
    TRANSCRIPTION_API_KEY: str = Field(description="API key for transcription service")
    TRANSCRIPTION_API_MODEL: str = Field(
        default="whisper-1", description="Model name for transcription API"
    )

    # Diarization API (custom endpoint)
    DIARIZATION_API_BASE_URL: str = Field(
        description="Base URL for diarization API endpoint"
    )
    DIARIZATION_API_KEY: str = Field(description="API key for diarization service")

    # Shared settings
    API_LANGUAGE: str = Field(
        default="fr", description="Language code for transcription"
    )
    API_TIMEOUT: Optional[float] = Field(
        default=None,
        description="API request timeout in seconds, None means no timeout",
    )
    MAX_RETRIES: int = Field(
        default=5,
        description="Number of retries for API requests on network errors",
    )
    BASE_RETRY_BACKOFF: int = Field(
        default=1,
        description="Number of seconds before the first retry. Grows exponentially by a factor of two at each retry",
    )
