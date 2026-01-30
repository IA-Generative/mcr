from io import BytesIO
from typing import List

import numpy as np
from faster_whisper import WhisperModel
from loguru import logger
from numpy.typing import NDArray
from openai import OpenAI

from mcr_meeting.app.configs.base import (
    TranscriptionApiSettings,
    WhisperTranscriptionSettings,
)
from mcr_meeting.app.schemas.transcription_schema import (
    TranscriptionSegment,
)
from mcr_meeting.app.services.speech_to_text.types import DiarizationSegment
from mcr_meeting.app.services.speech_to_text.utils.audio import (
    split_audio_on_timestamps,
)
from mcr_meeting.app.services.speech_to_text.utils.models import (
    get_transcription_model,
)

transcription_settings = WhisperTranscriptionSettings()
api_settings = TranscriptionApiSettings()


class TranscriptionProcessor:
    def __init__(self) -> None:
        self._openai_client: OpenAI | None = None

    def _get_openai_client(self) -> OpenAI:
        if self._openai_client is None:
            self._openai_client = OpenAI(
                api_key=api_settings.TRANSCRIPTION_API_KEY,
                base_url=api_settings.TRANSCRIPTION_API_BASE_URL,
            )
        return self._openai_client

    def transcribe(
        self,
        audio_bytes: BytesIO,
        vad_spans: List[DiarizationSegment],
    ) -> List[TranscriptionSegment]:
        transcription_inputs = split_audio_on_timestamps(audio_bytes, vad_spans)

        logger.debug("Number of transcription inputs: {}", len(transcription_inputs))

        transcription_model = get_transcription_model()
        transcription_segments: List[TranscriptionSegment] = []

        for idx, chunk in enumerate(transcription_inputs):
            logger.debug(
                "Transcribing vad chunk: start={}, end={}",
                chunk.diarization.start,
                chunk.diarization.end,
            )
            chunk_transcription_segments = self._transcribe_audio_chunk(
                chunk.audio, transcription_model
            )
            if not chunk_transcription_segments:
                logger.debug(
                    "No transcription for this chunk: start: {} - end: {}.",
                    chunk.diarization.start,
                    chunk.diarization.end,
                )
                continue
            logger.debug(
                "Number of transcription segments in one chunk: {}",
                len(chunk_transcription_segments),
            )

            for segment in chunk_transcription_segments:
                transcription_segments.append(
                    TranscriptionSegment(
                        id=idx,
                        start=segment.start + chunk.diarization.start,
                        end=segment.end + chunk.diarization.start,
                        text=segment.text,
                    )
                )

        return transcription_segments

    def _transcribe_audio_chunk(
        self,
        audio: NDArray[np.float32],
        transcription_model: WhisperModel,
    ) -> List[TranscriptionSegment]:
        return self._transcribe_audio_chunk_local(audio, transcription_model)

    def _transcribe_audio_chunk_local(
        self, audio: NDArray[np.float32], transcription_model: WhisperModel
    ) -> List[TranscriptionSegment]:
        logger.debug("Audio loaded shape: {}, dtype: {}", audio.shape, audio.dtype)

        segments, info = transcription_model.transcribe(
            audio,
            language=transcription_settings.language,
            word_timestamps=transcription_settings.word_timestamps,
            initial_prompt="Ceci est la transcription d'une réunion d'équipe avec plusieurs intervenants ; reformule le texte dans un langage naturel et fluide, sans répétitions.",
        )

        result = list(segments)

        logger.debug("Transcription info: {}", info)

        if not result:
            logger.debug("No segments found in transcription result.")
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
