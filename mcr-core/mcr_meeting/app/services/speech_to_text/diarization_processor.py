import tempfile
import time
from io import BytesIO

import httpx
from loguru import logger

from mcr_meeting.app.configs.base import (
    CelerySettings,
    PyannoteDiarizationParameters,
    TranscriptionApiSettings,
)
from mcr_meeting.app.exceptions.exceptions import DiarizationError
from mcr_meeting.app.infrastructure.unleash import (
    FeatureFlag,
    get_feature_flag_client,
)
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizationJobResponse,
    DiarizationJobStatus,
    DiarizationSegment,
)
from mcr_meeting.app.services.speech_to_text.utils import (
    convert_to_french_speaker,
)
from mcr_meeting.app.services.speech_to_text.utils.models import (
    get_diarization_pipeline,
)

api_settings = TranscriptionApiSettings()
diarization_params = PyannoteDiarizationParameters()
celery_settings = CelerySettings()


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
    def __init__(self) -> None:
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

    def _submit_diarization_job(self, audio_bytes: BytesIO) -> str:
        client = self._get_http_client()

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
        audio_bytes.seek(0)
        response.raise_for_status()

        job_id: str = response.json()["job_id"]
        logger.debug("Submitted async diarization job {}", job_id)
        return job_id

    def _diarize_async_api(self, audio_bytes: BytesIO) -> list[DiarizationSegment]:
        job_id = self._submit_diarization_job(audio_bytes)
        return self._poll_diarization_job(job_id)

    def _poll_diarization_job(self, job_id: str) -> list[DiarizationSegment]:
        url = f"{api_settings.DIARIZATION_API_BASE_URL}/jobs/audio/{job_id}"
        deadline = celery_settings.REDIS_VISIBILITY_TIMEOUT
        started_at = time.monotonic()
        cadence = _PollCadence(phase_started_at=started_at)
        transient_errors = 0

        while True:
            if time.monotonic() - started_at >= deadline:
                raise DiarizationError(
                    f"Diarization job {job_id} exceeded the {deadline}s deadline"
                )

            try:
                job_status = self._fetch_job_status(url, job_id)
            except httpx.HTTPError as e:
                transient_errors = self._register_transient_error(
                    job_id, transient_errors, e
                )
                time.sleep(api_settings.DIARIZATION_POLL_FAST_INTERVAL_SECONDS)
                continue

            transient_errors = 0
            segments = self._interpret_job_status(job_status, job_id)
            if segments is not None:
                return segments

            time.sleep(cadence.next_interval(job_status))

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
            raise

        return DiarizationJobResponse.model_validate(response.json())

    def _register_transient_error(
        self, job_id: str, transient_errors: int, error: httpx.HTTPError
    ) -> int:
        transient_errors += 1
        if transient_errors > api_settings.DIARIZATION_POLL_MAX_TRANSIENT_ERRORS:
            raise DiarizationError(
                f"Diarization job {job_id} polling failed after "
                f"{transient_errors} consecutive transient errors: {error}"
            ) from error

        logger.warning(
            "Transient error polling diarization job {} ({}/{}): {}",
            job_id,
            transient_errors,
            api_settings.DIARIZATION_POLL_MAX_TRANSIENT_ERRORS,
            error,
        )
        return transient_errors

    def _interpret_job_status(
        self, data: DiarizationJobResponse, job_id: str
    ) -> list[DiarizationSegment] | None:
        if data.status == DiarizationJobStatus.COMPLETED:
            return self._segments_from_result(data)

        if data.status == DiarizationJobStatus.FAILED:
            raise DiarizationError(f"Diarization job {job_id} failed: {data.error}")

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
