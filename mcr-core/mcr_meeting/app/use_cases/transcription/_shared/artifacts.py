from dataclasses import dataclass
from io import BytesIO

from mcr_meeting.app.schemas.transcription_schema import DiarizationSegment


@dataclass
class DiarizationArtifact:
    preprocessed_audio: BytesIO
    diarization: list[DiarizationSegment]
