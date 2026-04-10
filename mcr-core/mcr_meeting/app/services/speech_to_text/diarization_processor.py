import tempfile
from io import BytesIO

import httpx
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
                    retries=api_settings.MAX_RETRIES,
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
    ) -> list[DiarizationSegment]:
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

    def _diarize_local(self, audio_bytes: BytesIO) -> list[DiarizationSegment]:
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

    def _diarize_api(self, audio_bytes: BytesIO) -> list[DiarizationSegment]:
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

            logger.debug("API diarization returned {} segments", len(segments))

        except Exception as e:  
            raise DiarizationError(f"Error calling diarization API: {e}") from e  

        if not segments:  
            raise DiarizationError("Diarization API returned no segments")  

        return segments 

    def __del__(self) -> None:
        """Clean up HTTP client on deletion"""
        if self._http_client is not None:
            self._http_client.close()
