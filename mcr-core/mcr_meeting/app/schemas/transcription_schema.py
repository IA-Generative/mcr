from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field, field_validator

from mcr_meeting.app.exceptions.exceptions import UnknownDiarizationStatus


@dataclass
class TimeSpan:
    """Small helper to reason about time intervals in seconds."""

    start: float
    end: float

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(
                f"Invalid TimeSpan with end < start ({self.start} > {self.end})"
            )

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def midpoint(self) -> float:
        return (self.start + self.end) / 2.0

    def touches_or_overlaps(self, other: "TimeSpan") -> bool:
        return not (self.end < other.start or self.start > other.end)

    def overlap(self, other: "TimeSpan") -> float:
        start = max(self.start, other.start)
        end = min(self.end, other.end)
        return max(0.0, end - start)

    def merge(self, other: "TimeSpan") -> "TimeSpan":
        return TimeSpan(min(self.start, other.start), max(self.end, other.end))

    def gap_to(self, other: "TimeSpan") -> "TimeSpan | None":
        if self.end >= other.start:
            return None
        return TimeSpan(self.end, other.start)


class TranscriptionInput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    audio: NDArray[np.float32]
    span: TimeSpan


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


class Participant(BaseModel):
    speaker_id: str = Field(
        description="Identifiant unique du locuteur dans la transcription ex: LOCUTEUR_03.",
    )
    name: str | None = Field(
        None,
        description="Prenom et/ou nom déduit pour le locuteur à partir des interactions dans la transcription. Ex: 'Jean' ou 'Jean Dupont'.",
    )
    role: str | None = Field(
        None,
        description="Fonction/rôle si mentionné ou déduit (ex. PO, Tech Lead, Directeur financier).",
    )
    confidence: float | None = Field(
        ge=0.0,
        le=1.0,
        description="Niveau de confiance (entre 0 et 1) indiquant à quel point tu es certain du nom associé locuteur.",
    )
    association_justification: str | None = Field(
        description=(
            "Identification explicite ou déduction par contexte ayant permis d'associer ce nom/rôle au locuteur avec l'id."
        ),
    )


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
