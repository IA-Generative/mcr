from typing import Any

from pydantic import BaseModel


class DiarizationSegment(BaseModel):
    start: float
    end: float
    speaker: str


class TranscriptionInput(BaseModel):  # type: ignore[explicit-any]
    audio: Any  # type: ignore[explicit-any]
    diarization: DiarizationSegment  # permet de récupérer start et end de l'audio d'origine avant d'être splitté
