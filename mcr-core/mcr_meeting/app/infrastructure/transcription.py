from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import numpy as np
import soundfile as sf
from loguru import logger
from numpy.typing import NDArray
from openai import NotGiven, OpenAI

from mcr_meeting.app.configs.base import (
    TranscriptionApiSettings,
    WhisperTranscriptionSettings,
)
from mcr_meeting.app.domain.audio import split_audio_on_timestamps
from mcr_meeting.app.exceptions.exceptions import TranscriptionError
from mcr_meeting.app.schemas.transcription_schema import (
    TimeSpan,
    TranscriptionInput,
    TranscriptionSegment,
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
                max_retries=api_settings.MAX_RETRIES,
            )
        return self._openai_client

    def transcribe(
        self,
        audio_bytes: BytesIO,
        chunk_spans: list[TimeSpan],
    ) -> list[TranscriptionSegment]:
        transcription_inputs = split_audio_on_timestamps(audio_bytes, chunk_spans)

        logger.debug(
            "Starting transcription of {} input audio chunks", len(transcription_inputs)
        )

        def transcribe_one(
            indexed_chunk: tuple[int, TranscriptionInput],
        ) -> list[TranscriptionSegment]:
            idx, chunk = indexed_chunk
            chunk_transcription_segments = self._transcribe_audio_chunk_api(chunk.audio)
            if not chunk_transcription_segments:
                logger.debug(
                    "No transcription for this chunk: start: {} - end: {}.",
                    chunk.span.start,
                    chunk.span.end,
                )
                return []

            return [
                TranscriptionSegment(
                    id=idx,
                    start=segment.start + chunk.span.start,
                    end=segment.end + chunk.span.start,
                    text=segment.text,
                )
                for segment in chunk_transcription_segments
            ]

        with ThreadPoolExecutor(max_workers=api_settings.MAX_CONCURRENT_CHUNKS) as pool:
            results = pool.map(transcribe_one, enumerate(transcription_inputs))

            return [segment for chunk_segments in results for segment in chunk_segments]

    def _transcribe_audio_chunk_api(
        self,
        audio: NDArray[np.float32],
    ) -> list[TranscriptionSegment]:
        audio_bytes = BytesIO()
        sf.write(audio_bytes, audio, 16000, format="WAV")
        audio_bytes.seek(0)

        try:
            client = self._get_openai_client()

            prompt = transcription_settings.INITIAL_PROMPT or NotGiven()

            response = client.audio.transcriptions.create(
                model=api_settings.TRANSCRIPTION_API_MODEL,
                file=("audio.wav", audio_bytes, "audio/wav"),
                language=api_settings.API_LANGUAGE,
                response_format="verbose_json",
                prompt=prompt,
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

        except Exception as e:
            raise TranscriptionError(f"Error calling transcription API: {e}") from e

        if not segments:
            raise TranscriptionError("Transcription API returned no segments")

        return segments
