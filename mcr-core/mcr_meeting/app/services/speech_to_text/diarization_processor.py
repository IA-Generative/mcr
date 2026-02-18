import tempfile
from io import BytesIO
from typing import List

import httpx
import urllib3
from loguru import logger

from mcr_meeting.app.configs.base import (
    PyannoteDiarizationParameters,
    TranscriptionApiSettings,
)
from mcr_meeting.app.exceptions.exceptions import DiarizationError
from mcr_meeting.app.services.feature_flag_service import (
    FeatureFlag,
    get_feature_flag_client,
)
from mcr_meeting.app.services.speech_to_text.types import DiarizationSegment
from mcr_meeting.app.services.speech_to_text.utils import (
    convert_to_french_speaker,
)
from mcr_meeting.app.services.speech_to_text.utils.models import (
    get_diarization_pipeline,
)

api_settings = TranscriptionApiSettings()
diarization_params = PyannoteDiarizationParameters()


class DiarizationProcessor:
    def __init__(self) -> None:
        self._http_client: httpx.Client | None = None

    def _get_http_client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(
                timeout=api_settings.API_TIMEOUT,
                transport=httpx.HTTPTransport(
                    retries=urllib3.Retry(
                        total=api_settings.MAX_RETRIES,
                        allowed_methods=None,
                        backoff_factor=api_settings.BASE_RETRY_BACKOFF,
                    )
                ),
            )
        return self._http_client

    def _is_api_diarization_enabled(self) -> bool:
        try:
            feature_flag_client = get_feature_flag_client()
            return feature_flag_client.is_enabled(FeatureFlag.API_BASED_DIARIZATION)
        except Exception as e:
            logger.warning(
                "Failed to check diarization feature flag, defaulting to local mode: {}",
                e,
            )
            return False

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
        if self._is_api_diarization_enabled():
            return self._diarize_api(audio_bytes)
        else:
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

    def _diarize_api(self, audio_bytes: BytesIO) -> List[DiarizationSegment]:
        """Diarize using external API"""
        try:
            client = self._get_http_client()

            form_data = {
                "min_duration_off": diarization_params.min_duration_off,
                "clustering_threshold": diarization_params.threshold,
            }

            response = client.post(
                f"{api_settings.DIARIZATION_API_BASE_URL}/diarize",
                files={"file": ("audio.wav", audio_bytes, "audio/wav")},
                data=form_data,
                headers={"Authorization": f"Bearer {api_settings.DIARIZATION_API_KEY}"},
            )

            audio_bytes.seek(0)

            response.raise_for_status()
            data = response.json()

            logger.debug("Raw diarization API response: {}", data)

            # Parse response to DiarizationSegment format
            segments = []
            if "segments" in data:
                for segment_data in data["segments"]:
                    # Convert speaker labels to French format
                    speaker = convert_to_french_speaker(segment_data["speaker"])
                    segments.append(
                        DiarizationSegment(
                            start=segment_data["start"],
                            end=segment_data["end"],
                            speaker=speaker,
                        )
                    )

            logger.info("API diarization returned {} segments", len(segments))
            if segments:
                logger.debug(
                    "First 3 diarization segments: {}",
                    [(s.start, s.end, s.speaker) for s in segments[:3]],
                )
            return segments

        except Exception as e:
            raise DiarizationError("Error calling diarization API: {}", str(e))

    def __del__(self) -> None:
        """Clean up HTTP client on deletion"""
        if self._http_client is not None:
            self._http_client.close()
