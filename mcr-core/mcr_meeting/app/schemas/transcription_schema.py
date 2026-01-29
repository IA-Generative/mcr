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


class TranscriptionDocxResult(BaseModel):
    buffer: BytesIO
    filename: str

    class Config:
        arbitrary_types_allowed = True
