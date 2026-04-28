"""Config models for the Visio STT benchmark."""

from pathlib import Path

from pydantic import BaseModel, field_validator


class BotTask(BaseModel):
    audio: Path
    url: str

    @field_validator("audio")
    @classmethod
    def _audio_must_exist_and_be_wav(cls, v: Path) -> Path:
        if v.suffix.lower() != ".wav":
            raise ValueError(f"audio must be a .wav file, got {v.suffix!r}")
        if not v.exists():
            raise ValueError(f"audio file does not exist: {v}")
        return v


class BenchmarkConfig(BaseModel):
    tasks: list[BotTask]
    headless: bool = True
    post_stream_buffer_s: float = 3.0


def load_config(path: Path) -> BenchmarkConfig:
    return BenchmarkConfig.model_validate_json(path.read_text())
