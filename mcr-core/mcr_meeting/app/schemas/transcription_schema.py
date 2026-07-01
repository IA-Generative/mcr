from enum import StrEnum
from io import BytesIO

from pydantic import BaseModel, Field, field_validator

from mcr_meeting.app.exceptions.exceptions import UnknownDiarizationStatus


class SpeakerTranscription(BaseModel):
    """
    Speaker transcription model use to create new line
    in transcription database table
    """

    meeting_id: int = Field(description="meeting id")
    speaker: str = Field(description="speaker label")
    transcription_index: int = Field(description="transcribed sub-segment index")
    transcription: str = Field(description="transcription text")
    start: float = Field(description="start time in seconds", default=0.0)
    end: float = Field(description="end time in seconds", default=0.0)
    version: int = Field(
        default=0,
        description="transcription version. 0 for initial and other for corrected transcription",
    )


class TranscriptionSegment(BaseModel):
    id: int
    start: float
    end: float
    text: str


class DiarizedTranscriptionSegment(TranscriptionSegment):
    speaker: str

    def __str__(self) -> str:
        return f"{self.speaker}: {self.text}"


class TranscriptionDocxResult(BaseModel):
    buffer: BytesIO
    filename: str

    class Config:
        arbitrary_types_allowed = True


class DiarizationSegment(BaseModel):
    start: float
    end: float
    speaker: str


class DiarizationJobStatus(StrEnum):
    """Lifecycle statuses returned by the async diarization job API."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DiarizationJobResult(BaseModel):
    segments: list[DiarizationSegment]


class DiarizationJobResponse(BaseModel):
    status: DiarizationJobStatus
    queue_position: int | None = None
    error: str | None = None
    result: DiarizationJobResult | None = None

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: str) -> DiarizationJobStatus:
        try:
            return DiarizationJobStatus(value)
        except ValueError as e:
            raise UnknownDiarizationStatus(
                f"Diarization job returned unknown status {value!r}"
            ) from e
