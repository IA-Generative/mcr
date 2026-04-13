from io import BytesIO
from pathlib import Path

import pandas as pd
from loguru import logger

from mcr_meeting.app.services.s3_service import put_file_to_s3, s3_settings
from mcr_meeting.evaluation.asr.types import (
    EvaluationOutput,
    EvaluationSummary,
    TranscriptionOutput,
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
        self, result: TranscriptionOutput, uid: str, timestamp: str
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
        self, metrics_list: list[EvaluationOutput], timestamp: str
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
