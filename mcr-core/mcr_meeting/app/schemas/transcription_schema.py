from enum import StrEnum
from io import BytesIO

from pydantic import BaseModel, Field


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


class DiarizationJobStatus(StrEnum):
    """Lifecycle statuses returned by the async diarization job API."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DiarizationJobSegment(BaseModel):
    start: float
    end: float
    speaker: str


class DiarizationJobResult(BaseModel):
    segments: list[DiarizationJobSegment]


class DiarizationJobResponse(BaseModel):
    # `status` stays a plain str (not the enum) so an unexpected value surfaces as
    # our own UnknownDiarizationStatus downstream, not a pydantic ValidationError.
    status: str
    queue_position: int | None = None
    error: str | None = None
    result: DiarizationJobResult | None = None
