"""Speech to text service with speaker diarization using pyannote and faster-whisper"""

import tempfile
from io import BytesIO
from typing import Any, List, Optional

import httpx
import numpy as np
from loguru import logger
from numpy.typing import NDArray
from openai import OpenAI

from mcr_meeting.app.configs.base import (
    PyannoteDiarizationParameters,
    TranscriptionApiSettings,
    WhisperTranscriptionSettings,
)
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
    TranscriptionSegment,
)
from mcr_meeting.app.services.audio_pre_transcription_processing_service import (
    filter_noise_from_audio_bytes,
    normalize_audio_bytes_to_wav_bytes,
)
from mcr_meeting.app.services.feature_flag_service import (
    FeatureFlag,
    get_feature_flag_client,
)
from mcr_meeting.app.services.speech_to_text.types import DiarizationSegment
from mcr_meeting.app.services.speech_to_text.utils import (
    convert_to_french_speaker,
    diarize_vad_transcription_segments,
    get_vad_segments_from_diarization,
    set_diarization_pipeline,
    set_model,
    split_audio_on_timestamps,
)

transcription_settings = WhisperTranscriptionSettings()
diarization_settings = PyannoteDiarizationParameters()


class SpeechToTextPipeline:
    """Pipeline to convert speech in audio bytes to text with speaker diarization"""

    def __init__(self) -> None:
        self._api_settings: Optional[TranscriptionApiSettings] = None
        self._openai_client: Optional[OpenAI] = None
        self._http_client: Optional[httpx.Client] = None

    def _get_api_settings(self) -> TranscriptionApiSettings:
        """Lazy load API settings"""
        if self._api_settings is None:
            self._api_settings = TranscriptionApiSettings()
        return self._api_settings

    def _get_openai_client(self) -> OpenAI:
        """Lazy load OpenAI client"""
        if self._openai_client is None:
            settings = self._get_api_settings()
            self._openai_client = OpenAI(
                api_key=settings.TRANSCRIPTION_API_KEY,
                base_url=settings.TRANSCRIPTION_API_BASE_URL,
            )
        return self._openai_client

    def _get_http_client(self) -> httpx.Client:
        """Lazy load HTTP client"""
        if self._http_client is None:
            settings = self._get_api_settings()
            self._http_client = httpx.Client(timeout=settings.API_TIMEOUT)
        return self._http_client

    def _is_api_transcription_enabled(self) -> bool:
        """Check if API-based transcription is enabled via feature flag"""
        try:
            feature_flag_client = get_feature_flag_client()
            return feature_flag_client.is_enabled(FeatureFlag.API_BASED_TRANSCRIPTION)
        except Exception as e:
            logger.warning(
                "Failed to check transcription feature flag, defaulting to local mode: {}",
                e,
            )
            return False

    def _is_api_diarization_enabled(self) -> bool:
        """Check if API-based diarization is enabled via feature flag"""
        try:
            feature_flag_client = get_feature_flag_client()
            return feature_flag_client.is_enabled(FeatureFlag.API_BASED_DIARIZATION)
        except Exception as e:
            logger.warning(
                "Failed to check diarization feature flag, defaulting to local mode: {}",
                e,
            )

    def pre_process(self, audio_bytes: BytesIO) -> BytesIO:
        """Pre-process audio bytes before transcription and diarization.

        This includes normalizing the audio to WAV format and applying noise filtering if enabled.

        Args:
            audio_bytes (BytesIO): The input audio bytes.

        Returns:
            BytesIO: The pre-processed audio bytes.
        """
        feature_flag_client = get_feature_flag_client()
        normalized_audio_bytes = normalize_audio_bytes_to_wav_bytes(audio_bytes)
        # Apply noise filtering only if feature flag is enabled
        if feature_flag_client.is_enabled("audio_noise_filtering"):
            logger.debug("Noise filtering enabled")
            pre_processed_bytes = filter_noise_from_audio_bytes(normalized_audio_bytes)
        else:
            logger.debug("Noise filtering disabled, skipping filtering step")
            pre_processed_bytes = normalized_audio_bytes

        return pre_processed_bytes

    def transcribe(  # type: ignore[explicit-any]
        self,
        audio: NDArray[np.float32],
        model: Optional[Any] = None,
    ) -> List[TranscriptionSegment]:
        """Transcribe audio bytes to text with speaker diarization

        Args:
            audio (NDArray): The input audio array.
            transcription_settings (TranscriptionSettings): Settings for the transcription process.
            model (Optional[Any], optional): Pre-loaded transcription model. Defaults to None.

        Returns:
            List[TranscriptionSegment]: A list of TranscriptionSegment objects containing the transcription results with speaker labels.
        """
        if self._is_api_transcription_enabled():
            return self._transcribe_api(audio)
        else:
            return self._transcribe_local(audio, model)

    def _transcribe_local(
        self,
        audio: NDArray[np.float32],
        model: Optional[Any] = None,
    ) -> List[TranscriptionSegment]:
        """Transcribe using local faster-whisper model"""
        model = set_model(model)

        audio = audio.astype(np.float32, copy=False)
        logger.info("Audio loaded shape: {}, dtype: {}", audio.shape, audio.dtype)

        segments, info = model.transcribe(
            audio,
            language=transcription_settings.language,
            word_timestamps=transcription_settings.word_timestamps,
            initial_prompt="Ceci est la transcription d'une réunion d'équipe avec plusieurs intervenants ; reformule le texte dans un langage naturel et fluide, sans répétitions.",
        )

        result = list(segments)

        logger.debug("Transcription info: {}", info)

        if not result:
            logger.info("No segments found in transcription result.")
            return []

        transcription_segments = [
            TranscriptionSegment(
                id=seg.id,
                start=seg.start,
                end=seg.end,
                text=seg.text,
            )
            for seg in result
        ]

        return transcription_segments

    def _transcribe_api(
        self,
        audio: NDArray[np.float32],
    ) -> List[TranscriptionSegment]:
        """Transcribe using external API (OpenAI-compatible)"""
        # Convert numpy array to audio bytes
        import soundfile as sf

        audio_bytes = BytesIO()
        sf.write(audio_bytes, audio, 16000, format="WAV")
        audio_bytes.seek(0)

        try:
            api_settings = self._get_api_settings()
            client = self._get_openai_client()

            response = client.audio.transcriptions.create(
                model=api_settings.TRANSCRIPTION_API_MODEL,
                file=("audio.wav", audio_bytes, "audio/wav"),
                language=api_settings.API_LANGUAGE,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )

            # Convert API response to TranscriptionSegment format
            segments = []
            if hasattr(response, "segments") and response.segments:
                for idx, segment in enumerate(response.segments):
                    segments.append(
                        TranscriptionSegment(
                            id=idx,
                            start=segment.start,
                            end=segment.end,
                            text=segment.text,
                        )
                    )

            logger.info("API transcription returned {} segments", len(segments))
            return segments

        except Exception as e:
            logger.error("Error calling transcription API: {}", str(e))
            raise

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
        diarization_pipeline = set_diarization_pipeline()

        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp_audio:
            tmp_audio.write(audio_bytes.getvalue())
            tmp_audio_path = tmp_audio.name

            pyannote_diarization = diarization_pipeline(tmp_audio_path)

            diarization = [
                DiarizationSegment(
                    start=segment.start,
                    end=segment.end,
                    speaker=convert_to_french_speaker(speaker),
                )
                for segment, _, speaker in pyannote_diarization.itertracks(
                    yield_label=True
                )
            ]

            return diarization

    def _diarize_api(self, audio_bytes: BytesIO) -> List[DiarizationSegment]:
        """Diarize using external API"""
        try:
            settings = self._get_api_settings()
            client = self._get_http_client()

            response = client.post(
                f"{settings.DIARIZATION_API_BASE_URL}/diarize",
                files={"file": ("audio.wav", audio_bytes, "audio/wav")},
                headers={"Authorization": f"Bearer {settings.DIARIZATION_API_KEY}"},
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

        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error from diarization API: {} - {}",
                e.response.status_code,
                e.response.text,
            )
            raise
        except Exception as e:
            logger.error("Error calling diarization API: {}", str(e))
            raise

    def run(  # type: ignore[explicit-any]
        self,
        audio_bytes: BytesIO,
        model: Optional[Any] = None,
    ) -> List[DiarizedTranscriptionSegment]:
        """Transcribe full audio bytes to text with speaker diarization"""

        logger.debug("Starting speech-to-text pipeline with pre-processing.")

        pre_processed_audio_bytes = self.pre_process(audio_bytes)

        logger.info("Running diarization with {}", diarization_settings)

        diarization_result = self.diarize(
            pre_processed_audio_bytes,
        )

        if not diarization_result:
            logger.info("No diarization result. Returning empty transcription.")
            return []

        vad_spans: List[DiarizationSegment] = get_vad_segments_from_diarization(
            diarization_result
        )

        vad_transcription_inputs = split_audio_on_timestamps(
            pre_processed_audio_bytes, vad_spans
        )

        vad_transcription_segments: List[TranscriptionSegment] = []

        logger.info("Number of diarization chunks: {}", len(diarization_result))

        for idx, chunk in enumerate(vad_transcription_inputs):
            logger.info(
                "Transcribing vad chunk: start={}, end={}",
                chunk.diarization.start,
                chunk.diarization.end,
            )
            chunk_transcription_segments = self.transcribe(chunk.audio, model=model)
            if not chunk_transcription_segments:
                logger.info(
                    "No transcription for this chunk: start: {} - end: {}.",
                    chunk.diarization.start,
                    chunk.diarization.end,
                )
                continue
            logger.info(
                "Number of transcription segments in one chunk: {}",
                len(chunk_transcription_segments),
            )

            for segment in chunk_transcription_segments:
                vad_transcription_segments.append(
                    TranscriptionSegment(
                        id=idx,
                        start=segment.start + chunk.diarization.start,
                        end=segment.end + chunk.diarization.start,
                        text=segment.text,
                    )
                )

        transcription_segments = diarize_vad_transcription_segments(
            vad_transcription_segments, diarization_result
        )

        logger.debug("Final transcription segments: {}", transcription_segments)
        return transcription_segments

    def __del__(self):
        """Clean up HTTP client on deletion"""
        if self._http_client is not None:
            self._http_client.close()
