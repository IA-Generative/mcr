from io import BytesIO
from pathlib import Path
from typing import List, Optional

import pandas as pd
from jiwer import cer, wer
from loguru import logger
from pyannote.core import Annotation, Segment
from pyannote.metrics.diarization import (
    DiarizationCompleteness,
    DiarizationCoverage,
    DiarizationErrorRate,
)

from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
)
from mcr_meeting.app.services.audio_pre_transcription_processing_service import (
    filter_noise_from_audio_bytes,
    normalize_audio_bytes_to_wav_bytes,
)
from mcr_meeting.app.services.feature_flag_service import (
    FeatureFlagClient,
    get_feature_flag_client,
)
from mcr_meeting.app.services.meeting_to_transcription_service import (
    merge_consecutive_segments_per_speaker,
)
from mcr_meeting.app.services.s3_service import put_file_to_s3, s3_settings
from mcr_meeting.app.services.transcription_engine_service import (
    speech_to_text_transcription,
)
from mcr_meeting.evaluation.eval_types import (
    DiarizationMetrics,
    EvaluationInput,
    EvaluationMetrics,
    EvaluationOutput,
    EvaluationSummary,
    TranscriptionMetrics,
    TranscriptionResult,
)


class AudioFileProcessor:
    """Handles audio file processing and transcription"""

    def __init__(
        self,
        model: Optional[object] = None,
        feature_flag_client: Optional[FeatureFlagClient] = None,
    ):
        """Initialize with an optional ASR model and feature flag client"""
        self.is_model_specified = False
        if model is not None:
            logger.info("Using specified model for transcription: {}", model)
            self.model = model
            self.is_model_specified = True
        self.feature_flag_client = feature_flag_client

    def process_audio_file(self, audio_bytes: BytesIO) -> TranscriptionResult:
        """Process a single audio file and return transcription result"""

        normalized_bytes = normalize_audio_bytes_to_wav_bytes(audio_bytes)

        feature_flag_client = get_feature_flag_client()

        # Apply noise filtering only if feature flag is enabled
        if feature_flag_client and feature_flag_client.is_enabled(
            "audio_noise_filtering"
        ):
            logger.info("Noise filtering enabled")
            processed_bytes = filter_noise_from_audio_bytes(normalized_bytes)
        else:
            logger.info("Noise filtering disabled, skipping filtering step")
            processed_bytes = normalized_bytes

        raw_transcription = (
            speech_to_text_transcription(audio_bytes=processed_bytes, model=self.model)
            if self.is_model_specified
            else speech_to_text_transcription(audio_bytes=processed_bytes)
        )

        transcription = merge_consecutive_segments_per_speaker(raw_transcription)

        text = " ".join(seg.text for seg in transcription)
        return TranscriptionResult(text=text, segments=transcription)


def extract_reference_text(ref_data: TranscriptionResult) -> str:
    """Extract reference text from reference data"""
    if ref_data.text:
        return ref_data.text
    if ref_data.segments:
        return " ".join(seg.text for seg in ref_data.segments)
    raise ValueError("No valid reference text found in reference data")


class MetricsCalculator:
    """Handles calculation of evaluation metrics"""

    @staticmethod
    def calculate_transcription_metrics(
        reference_text: str,
        hypothesis_text: str,
    ) -> TranscriptionMetrics:
        """Calculate WER and CER metrics for a single file"""
        wer_score = wer(reference_text, hypothesis_text)
        cer_score = cer(reference_text, hypothesis_text)
        return TranscriptionMetrics(wer=round(wer_score, 4), cer=round(cer_score, 4))

    @staticmethod
    def calculate_diarization_metrics(
        reference_segments: List[DiarizedTranscriptionSegment],
        hypothesis_segments: List[DiarizedTranscriptionSegment],
    ) -> DiarizationMetrics:
        """Calculate Diarization Error Rate (DER)"""

        ref_annot = Annotation()
        for seg in reference_segments:
            ref_annot[Segment(seg.start, seg.end)] = seg.speaker

        hyp_annot = Annotation()
        for seg in hypothesis_segments:
            hyp_annot[Segment(seg.start, seg.end)] = seg.speaker

        der_metric = DiarizationErrorRate()
        coverage_metric = DiarizationCoverage()
        completeness_metric = DiarizationCompleteness()

        der_value = der_metric(ref_annot, hyp_annot)
        coverage_value = coverage_metric(ref_annot, hyp_annot)
        completeness_value = completeness_metric(ref_annot, hyp_annot)

        return DiarizationMetrics(
            error_rate=round(der_value, 3),
            coverage=round(coverage_value, 3),
            completeness=round(completeness_value, 3),
        )

    def calculate_metrics(
        self,
        sample: EvaluationInput,
        hypothesis_transcription: TranscriptionResult,
    ) -> Optional[EvaluationMetrics]:
        """Calculate metrics for a single file"""
        if not sample.reference_transcription:
            logger.warning(
                "Reference transcription is empty. Cannot calculate metrics for {}",
                sample.uid,
            )
            return None

        logger.info("Calculating metrics for {}", sample.uid)
        reference_text = extract_reference_text(sample.reference_transcription)
        generated_text = " ".join(seg.text for seg in hypothesis_transcription.segments)
        transcription_metrics = self.calculate_transcription_metrics(
            reference_text, generated_text
        )

        diarization_metrics = self.calculate_diarization_metrics(
            sample.reference_transcription.segments,
            hypothesis_transcription.segments,
        )

        return EvaluationMetrics(
            uid=sample.uid,
            wer=transcription_metrics.wer,
            cer=transcription_metrics.cer,
            diarization_error_rate=diarization_metrics.error_rate,
            diarization_coverage=diarization_metrics.coverage,
            diarization_completeness=diarization_metrics.completeness,
        )


class ResultsManager:
    """Handles saving and managing evaluation results"""

    def __init__(self, output_dir: Path, dev: bool = True):
        self.output_dir = output_dir
        self.dev = dev
        self.bucket = s3_settings.S3_BUCKET
        self.folder = s3_settings.S3_EVALUATION_FOLDER
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_generated_transcription(
        self, result: TranscriptionResult, uid: str, timestamp: str
    ) -> None:
        """Save transcription result to JSON file if in dev mode"""
        if not self.dev:
            logger.info("Saving generated transcription to s3 in deployed mode")
            self.save_json_to_s3(
                BytesIO(result.model_dump_json(indent=2).encode("utf-8")),
                f"hypothesis_transcription/{timestamp}_{uid}.json",
            )
            return

        output_path = self.output_dir / f"{timestamp}_{uid}.json"
        logger.info("Saving transcription result for {} at {}", uid, timestamp)
        with open(output_path, "w") as f:
            f.write(result.model_dump_json(indent=2))
        logger.info("Saved transcription result to: {}", output_path)

    def save_metrics_csv(
        self, metrics_list: List[EvaluationOutput], timestamp: str
    ) -> None:
        """Save evaluation metrics to CSV file"""
        if not self.dev:
            logger.warning("Metrics saving is disabled in non-dev mode")
            return
        if not metrics_list:
            raise ValueError("No metrics to save")
        logger.debug("Saving metrics to CSV")
        df = pd.DataFrame(
            [
                {
                    "uid": m.uid,
                    "wer": m.metrics.wer,
                    "cer": m.metrics.cer,
                    "diarization_error_rate": m.metrics.diarization_error_rate,
                    "diarization_coverage": m.metrics.diarization_coverage,
                    "diarization_completeness": m.metrics.diarization_completeness,
                }
                for m in metrics_list
            ]
        )
        output_path = self.output_dir / f"{timestamp}_metrics.csv"
        df.to_csv(output_path, index=False)
        logger.info("Saved metrics CSV to: {}", output_path)

    def save_summary_json(self, summary: EvaluationSummary, timestamp: str) -> None:
        """Save evaluation summary to JSON file"""
        if not self.dev:
            logger.warning("Summary saving is disabled in non-dev mode")
            return
        output_path = self.output_dir / f"{timestamp}_summary.json"
        with open(output_path, "w") as f:
            f.write(summary.model_dump_json(indent=2))
        logger.info("Saved summary JSON to: {}", output_path)

    def save_results_to_s3(self, df: pd.DataFrame, object_name: str) -> None:
        """Save results DataFrame to S3"""

        if self.dev:
            logger.warning("Results saving in s3 is disabled in dev mode")
            return

        csv_bytes = df.to_csv(index=False).encode("utf-8")

        content_type = "text/csv"

        object_name = f"{self.folder}/{object_name}" if self.folder else object_name

        logger.info(
            "Saving results to S3 bucket '{}' with object name '{}'",
            self.bucket,
            object_name,
        )

        put_file_to_s3(
            content=BytesIO(csv_bytes),
            object_name=object_name,
            content_type=content_type,
        )

    def save_json_to_s3(self, json_bytes: BytesIO, object_name: str) -> None:
        """Save JSON bytes to S3"""

        if self.dev:
            logger.warning("JSON saving in s3 is disabled in dev mode")
            return

        content_type = "application/json"

        object_name = f"{self.folder}/{object_name}" if self.folder else object_name

        logger.info(
            "Saving JSON to S3 bucket '{}' with object name '{}'",
            self.bucket,
            object_name,
        )

        put_file_to_s3(
            content=json_bytes,
            object_name=object_name,
            content_type=content_type,
        )
