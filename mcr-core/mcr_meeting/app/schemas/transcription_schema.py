from io import BytesIO
from typing import Any, Dict, List, Optional, Protocol

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


class TranscriptionWord(BaseModel):
    text: str = Field(description="Transcribe text")
    start: float = Field(
        description="Relative start time (in ms) of the segment int the audio file"
    )
    end: float = Field(
        description="Relative end time (in ms) of the segment int the audio file"
    )
    confidence: float


class TranscriptionSegment(BaseModel):
    id: int
    start: float
    end: float
    text: str
    speaker: Optional[str] = None


class TranscriptionResponse(BaseModel):  # type: ignore[explicit-any]
    text: str
    segments: List[TranscriptionSegment]
    language: Optional[str] = "fr"
    speech_activity: Optional[List[Dict[str, Any]]] = None  # type: ignore[explicit-any]


class FullTranscription(BaseModel):
    """
    Model use to retrieve all transcription saved in database for a specific
    meeting and merge all consecutive transcription linked to a same speaker.
    """

    meeting_id: int = Field(description="meeting id")
    speaker: str = Field(description="speaker id or label")
    transcription: str = Field(description="transcription")


class TranscriptionPipeline(Protocol):
    def __call__(
        self,
        meeting_id: int,
    ) -> Optional[List[SpeakerTranscription]]: ...


class TranscriptionDocxResult(BaseModel):
    buffer: BytesIO
    filename: str

    class Config:
        arbitrary_types_allowed = True
