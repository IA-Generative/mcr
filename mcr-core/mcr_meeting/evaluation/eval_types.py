from io import BytesIO
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from mcr_meeting.app.schemas.transcription_schema import TranscriptionSegment


class TranscriptionResult(BaseModel):
    text: str
    segments: List[TranscriptionSegment]


class EvaluationMetrics(BaseModel):
    uid: str
    wer: float
    cer: float
    diarization_error_rate: float
    diarization_coverage: float
    diarization_completeness: float


class TranscriptionMetrics(BaseModel):
    wer: float
    cer: float


class DiarizationMetrics(BaseModel):
    error_rate: float
    coverage: float
    completeness: float


class EvaluationSummary(BaseModel):
    wer_mean: float
    cer_mean: float
    der_mean: float
    diarization_coverage_mean: float
    diarization_completeness_mean: float
    total_files: int


class EvaluationInput(BaseModel):
    uid: str
    audio_path: Path
    audio_bytes: Optional[BytesIO] = None
    reference_transcription: Optional[TranscriptionResult] = None
    generated_transcription: Optional[TranscriptionResult] = None

    class Config:
        arbitrary_types_allowed = True


class EvaluationOutput(BaseModel):
    uid: str
    reference_transcription: TranscriptionResult
    generated_transcription: TranscriptionResult
    metrics: EvaluationMetrics

    class Config:
        arbitrary_types_allowed = True
