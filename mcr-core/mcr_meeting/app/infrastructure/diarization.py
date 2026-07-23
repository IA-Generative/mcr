import re
import tempfile
import time
from collections.abc import Callable
from io import BytesIO

import httpx
from loguru import logger
from pyannote.audio import Pipeline

from mcr_meeting.app.configs.base import (
    CelerySettings,
    PyannoteDiarizationParameters,
    RetrySettings,
    TranscriptionApiSettings,
)
from mcr_meeting.app.domain.transcription.speaker_segments import (
    convert_to_french_speaker,
)
from mcr_meeting.app.exceptions.exceptions import (
    DiarizationError,
    DiarizationRetryableError,
    DiarizationTransientError,
)
from mcr_meeting.app.infrastructure.retry import retry_transient
from mcr_meeting.app.infrastructure.unleash import (
    FeatureFlag,
    get_feature_flag_client,
)
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizationJobResponse,
    DiarizationJobStatus,
    DiarizationSegment,
)

api_settings = TranscriptionApiSettings()
diarization_params = PyannoteDiarizationParameters()
celery_settings = CelerySettings()
_retry_settings = RetrySettings()

# Job `error` is free text (no structured code) but the diarization job server
# emits a fixed, category-prefixed vocabulary. Source of truth:
#   https://github.com/IA-Generative/kevent-ai
#   (gateway kevent-gateway-0.14.1 / relay relay-v0.11.0, HEAD 6a8ffb8)
#   - "stale: pending too long"                          internal/storage/redis.go
#   - "inference: inference endpoint returned <code>: …" relay .../adapter/multipart.go
#   - "inference: calling inference endpoint: …"         relay .../adapter/multipart.go
#   - "input file not found[: …]"                        relay .../relay/relay.go (permanent)
# Retryable = the whole job can be resubmitted and later succeed (backlog drains,
# inference backend recovers). Everything else (4xx input errors, missing input,
# unknown reasons) is permanent — fail loud rather than retry-storm.
_INFERENCE_5XX = re.compile(r"returned 5\d\d")


def _is_retryable_failure(error: str | None) -> bool:
    if error is None:
        return False
    reason = error.lower()
    if reason.startswith("stale:"):
        return True
    if reason.startswith("inference:"):
        # Backend down/cold (5xx) or unreachable → resubmit; a 4xx is a bad
        # request/input the server won't accept on replay → permanent.
        return "calling inference endpoint" in reason or bool(
            _INFERENCE_5XX.search(reason)
        )
    return False


def next_poll_interval(phase_elapsed_s: float, queue_position: int | None) -> float:
    near_front = queue_position is not None and queue_position <= 1
    short_guess = (
        phase_elapsed_s < api_settings.DIARIZATION_POLL_LONG_AUDIO_THRESHOLD_SECONDS
    )
    if near_front or short_guess:
        return api_settings.DIARIZATION_POLL_FAST_INTERVAL_SECONDS
    return api_settings.DIARIZATION_POLL_SLOW_INTERVAL_SECONDS


class _PollCadence:
    def __init__(self, phase_started_at: float) -> None:
        self._phase_started_at = phase_started_at
        self._seen_processing = False

    def next_interval(self, data: DiarizationJobResponse) -> float:
        if data.status == DiarizationJobStatus.PROCESSING and not self._seen_processing:
            self._seen_processing = True
            self._phase_started_at = time.monotonic()

        phase_elapsed = time.monotonic() - self._phase_started_at
        return next_poll_interval(phase_elapsed, data.queue_position)


class DiarizationProcessor:
    def __init__(self, pipeline_provider: Callable[[], Pipeline] | None = None) -> None:
        self._pipeline_provider = pipeline_provider
        self._http_client: httpx.Client | None = None

    def _get_http_client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(
                timeout=api_settings.DIARIZATION_POLL_HTTP_TIMEOUT_SECONDS,
                headers={"Authorization": f"Bearer {api_settings.DIARIZATION_API_KEY}"},
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
            return self._diarize_async_api(audio_bytes)
        else:
            return self._diarize_local(audio_bytes)

    def _diarize_local(self, audio_bytes: BytesIO) -> list[DiarizationSegment]:
        if self._pipeline_provider is None:
            raise DiarizationError(
                "Local diarization requested but no pipeline provider was injected"
            )
        diarization_pipeline = self._pipeline_provider()

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

    @retry_transient(
        on=(DiarizationTransientError,),
        attempts=_retry_settings.DIARIZATION_RETRY_ATTEMPTS,
        initial_delay=_retry_settings.DIARIZATION_RETRY_INITIAL_DELAY,
        max_delay=_retry_settings.DIARIZATION_RETRY_MAX_DELAY,
    )
    def _submit_diarization_job(self, audio_bytes: BytesIO) -> str:
        client = self._get_http_client()

        # Reset before (not only after) the POST so a local retry re-reads from
        # the start rather than an already-consumed buffer.
        audio_bytes.seek(0)
        try:
            response = client.post(
                f"{api_settings.DIARIZATION_API_BASE_URL}/jobs/audio",
                files={"file": ("audio.wav", audio_bytes, "audio/wav")},
                data={
                    "operation": "diarization",
                    "model": api_settings.DIARIZATION_API_MODEL,
                    "min_duration_off": diarization_params.min_duration_off,
                    "clustering_threshold": diarization_params.threshold,
                },
            )
            response.raise_for_status()
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            # Proven never reached the server → no job created → safe fast replay.
            raise DiarizationTransientError(
                f"Transient error submitting diarization job: {e}"
            ) from e
        except httpx.HTTPStatusError as e:
            if e.response.status_code < 500:
                raise DiarizationError(
                    f"Diarization job submission rejected "
                    f"(HTTP {e.response.status_code})"
                ) from e
            raise DiarizationTransientError(
                f"Transient error submitting diarization job "
                f"(HTTP {e.response.status_code})"
            ) from e
        except httpx.HTTPError as e:
            # Ambiguous post-send failure (e.g. ReadTimeout): the upload may have
            # created a job we can't recover the id for, so a replay can duplicate
            # it. Retry only at the task level (backoff), never fast in-process;
            # a duplicate job is harmless waste, a dead meeting is worse.
            raise DiarizationRetryableError(
                f"Retryable error submitting diarization job: {e}"
            ) from e

        job_id: str = response.json()["job_id"]
        logger.debug("Submitted async diarization job {}", job_id)
        return job_id

    def _diarize_async_api(self, audio_bytes: BytesIO) -> list[DiarizationSegment]:
        job_id = self._submit_diarization_job(audio_bytes)
        return self._poll_diarization_job(job_id)

    def _poll_diarization_job(self, job_id: str) -> list[DiarizationSegment]:
        # This loop only inspects the job status and controls the clock; network
        # errors are handled (and retried) inside _fetch_job_status.
        url = f"{api_settings.DIARIZATION_API_BASE_URL}/jobs/audio/{job_id}"
        deadline = celery_settings.REDIS_VISIBILITY_TIMEOUT
        started_at = time.monotonic()
        cadence = _PollCadence(phase_started_at=started_at)

        while True:
            if time.monotonic() - started_at >= deadline:
                raise DiarizationError(
                    f"Diarization job {job_id} exceeded the {deadline}s deadline"
                )

            job_status = self._fetch_job_status(url, job_id)

            segments = self._interpret_job_status(job_status, job_id)
            if segments is not None:
                return segments

            time.sleep(cadence.next_interval(job_status))

    @retry_transient(
        on=(DiarizationTransientError,),
        # Polling is an idempotent GET, so tolerate a sustained blip in-process
        # before giving up to the task level; budget mirrors the old counter.
        attempts=api_settings.DIARIZATION_POLL_MAX_TRANSIENT_ERRORS,
        initial_delay=_retry_settings.DIARIZATION_RETRY_INITIAL_DELAY,
        max_delay=api_settings.DIARIZATION_POLL_FAST_INTERVAL_SECONDS,
    )
    def _fetch_job_status(self, url: str, job_id: str) -> DiarizationJobResponse:
        client = self._get_http_client()
        try:
            response = client.get(url)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                raise DiarizationError(
                    f"Diarization job {job_id} polling unauthorized "
                    f"(HTTP {e.response.status_code})"
                ) from e
            raise DiarizationTransientError(
                f"Transient error polling diarization job {job_id} "
                f"(HTTP {e.response.status_code})"
            ) from e
        except httpx.HTTPError as e:
            raise DiarizationTransientError(
                f"Transient error polling diarization job {job_id}: {e}"
            ) from e

        return DiarizationJobResponse.model_validate(response.json())

    def _interpret_job_status(
        self, data: DiarizationJobResponse, job_id: str
    ) -> list[DiarizationSegment] | None:
        if data.status == DiarizationJobStatus.COMPLETED:
            return self._segments_from_result(data)

        if data.status == DiarizationJobStatus.FAILED:
            message = f"Diarization job {job_id} failed: {data.error}"
            if _is_retryable_failure(data.error):
                # Server job is dead (no live duplicate) but a fresh submit after
                # backoff can succeed once the backlog drains / model recovers.
                raise DiarizationRetryableError(message)
            raise DiarizationError(message)

        return None

    @staticmethod
    def _segments_from_result(data: DiarizationJobResponse) -> list[DiarizationSegment]:
        # result.segments carries pyannote-labelled segments (SPEAKER_00);
        # same shape/output as the local path so nothing downstream changes.
        if data.result is None:
            raise DiarizationError("Diarization job completed without a result")

        segments = [
            DiarizationSegment(
                start=segment.start,
                end=segment.end,
                speaker=convert_to_french_speaker(segment.speaker),
            )
            for segment in data.result.segments
        ]
        if not segments:
            raise DiarizationError("Diarization job completed with no segments")
        return segments

    def __del__(self) -> None:
        """Clean up HTTP client on deletion"""
        if self._http_client is not None:
            self._http_client.close()
