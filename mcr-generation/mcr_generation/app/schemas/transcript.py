from pydantic import BaseModel


class FullTranscriptSegment(BaseModel):
    speaker: str
    transcription_index: int
    transcription: str
    start: float
    end: float


class FullTranscript(BaseModel):
    meeting_id: int
    version: int = 0
    segments: list[FullTranscriptSegment]
