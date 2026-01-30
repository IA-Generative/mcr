import tempfile
from io import BytesIO
from typing import List

import httpx

from mcr_meeting.app.configs.base import (
    TranscriptionApiSettings,
)
from mcr_meeting.app.services.speech_to_text.types import DiarizationSegment
from mcr_meeting.app.services.speech_to_text.utils import (
    convert_to_french_speaker,
)
from mcr_meeting.app.services.speech_to_text.utils.models import (
    get_diarization_pipeline,
)

api_settings = TranscriptionApiSettings()


class DiarizationProcessor:
    def __init__(self) -> None:
        self._http_client: httpx.Client | None = None

    def _get_http_client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=api_settings.API_TIMEOUT)
        return self._http_client

    def diarize(
        self,
        audio_bytes: BytesIO,
    ) -> List[DiarizationSegment]:
        """Perform speaker diarization on audio bytes

        Args:
            audio_bytes (BytesIO): The input audio bytes.

        Returns:
            List[DiarizationSegment]: The diarization result with speaker segments.
        """
        return self._diarize_local(audio_bytes)

    def _diarize_local(self, audio_bytes: BytesIO) -> List[DiarizationSegment]:
        """Diarize using local pyannote model"""
        diarization_pipeline = get_diarization_pipeline()

        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp_audio:
            tmp_audio.write(audio_bytes.getvalue())
            tmp_audio_path = tmp_audio.name

            pyannote_diarization = diarization_pipeline(tmp_audio_path)

            diarization_segments = [
                DiarizationSegment(
                    start=segment.start,
                    end=segment.end,
                    speaker=convert_to_french_speaker(speaker),
                )
                for segment, _, speaker in pyannote_diarization.itertracks(
                    yield_label=True
                )
            ]

            return diarization_segments

    def __del__(self) -> None:
        """Clean up HTTP client on deletion"""
        if self._http_client is not None:
            self._http_client.close()
