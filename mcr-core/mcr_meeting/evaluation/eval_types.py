from io import BytesIO
from pathlib import Path
from typing import List

from pydantic import BaseModel

from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment


class TranscriptionOutput(BaseModel):
    segments: List[DiarizedTranscriptionSegment]

    @property
    def text(self) -> str:
        return " ".join(segment.text for segment in self.segments)


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
    audio_bytes: BytesIO
    reference_transcription: TranscriptionOutput

    class Config:
        arbitrary_types_allowed = True


class MetricsPipelineInput(EvaluationInput):
    generated_transcription: TranscriptionOutput


class EvaluationOutput(BaseModel):
    uid: str
    reference_transcription: TranscriptionOutput
    generated_transcription: TranscriptionOutput
    metrics: EvaluationMetrics

    class Config:
        arbitrary_types_allowed = True
