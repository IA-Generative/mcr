from collections import deque
from collections.abc import Callable, Iterable
from concurrent.futures import Future, ThreadPoolExecutor
from io import BytesIO
from typing import TypeVar

import numpy as np
import soundfile as sf
from loguru import logger
from numpy.typing import NDArray
from openai import APIConnectionError, APIStatusError, NotGiven, OpenAI

from mcr_meeting.app.configs.base import (
    TranscriptionApiSettings,
    WhisperTranscriptionSettings,
)
from mcr_meeting.app.domain.audio import iter_audio_chunks
from mcr_meeting.app.exceptions.exceptions import (
    TranscriptionError,
    TranscriptionTransientError,
)
from mcr_meeting.app.infrastructure.sentry import span
from mcr_meeting.app.schemas.transcription_schema import (
    TimeSpan,
    TranscriptionInput,
    TranscriptionSegment,
)

transcription_settings = WhisperTranscriptionSettings()
api_settings = TranscriptionApiSettings()

T = TypeVar("T")
R = TypeVar("R")


def _map_bounded(
    pool: ThreadPoolExecutor,
    work: Callable[[T], R],
    items: Iterable[T],
    limit: int,
) -> list[R]:
    in_flight: deque[Future[R]] = deque()
    results: list[R] = []

    for item in items:
        if len(in_flight) >= limit:
            results.append(in_flight.popleft().result())
        in_flight.append(pool.submit(work, item))

    results.extend(future.result() for future in in_flight)
    return results


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

        # A parent span for the whole fan-out. The per-chunk API calls run in
        # worker threads whose spans don't nest here (Sentry's scope is
        # thread-local), but this still turns total transcription time into one
        # named span instead of scattered, orphaned child spans.
        with span("transcription.transcribe", "transcribe") as transcribe_span:
            transcribe_span.set_data("transcription.chunk_count", len(chunk_spans))

            logger.debug(
                "Starting transcription of {} input audio chunks",
                len(chunk_spans),
            )

            chunks = enumerate(iter_audio_chunks(audio_bytes, chunk_spans))

            with ThreadPoolExecutor(
                max_workers=api_settings.MAX_CONCURRENT_CHUNKS
            ) as pool:
                results = _map_bounded(
                    pool, transcribe_one, chunks, api_settings.MAX_CONCURRENT_CHUNKS
                )

                return [
                    segment for chunk_segments in results for segment in chunk_segments
                ]

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

        except APIStatusError as e:
            # 5xx (backend down/cold) and 429 (overload) recover on a whole-op
            # replay; a 4xx is a request the server rejects on replay → permanent.
            if e.status_code == 429 or e.status_code >= 500:
                raise TranscriptionTransientError(
                    f"Transient transcription API error (HTTP {e.status_code})"
                ) from e
            raise TranscriptionError(
                f"Transcription API rejected the request (HTTP {e.status_code})"
            ) from e
        except APIConnectionError as e:
            # Covers APITimeoutError. Connect blip / timeout on a stateless POST.
            raise TranscriptionTransientError(
                f"Transient error calling transcription API: {e}"
            ) from e
        except Exception as e:
            # Unknown fault → fail loud rather than retry-storm.
            raise TranscriptionError(f"Error calling transcription API: {e}") from e

        if not segments:
            raise TranscriptionError("Transcription API returned no segments")

        return segments
