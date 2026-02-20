import os
from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd
from loguru import logger

from mcr_meeting.app.services.speech_to_text.speech_to_text import SpeechToTextPipeline
from mcr_meeting.evaluation.eval_types import (
    EvaluationInput,
    EvaluationOutput,
    EvaluationSummary,
    MetricsPipelineInput,
    TranscriptionOutput,
)
from mcr_meeting.evaluation.utils import (
    MetricsCalculator,
    ResultsManager,
)


class ASREvaluationPipeline:
    """Main pipeline orchestrator for Automatic Speech Recognition (ASR) evaluation"""

    def __init__(self, inputs: List[EvaluationInput]):
        self.inputs = inputs
        self.dev = os.environ.get("ENV_MODE") == "DEV"
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.speech_to_text_pipeline = SpeechToTextPipeline()
        self.metrics_manager = MetricsPipeline()

    def process_single_sample(
        self, sample: EvaluationInput, results_manager: ResultsManager
    ) -> MetricsPipelineInput | None:
        """Process a single audio file and return evaluation metrics"""
        try:
            logger.info("Processing sample {}...", sample.uid)

            generated_transcription_segments = self.speech_to_text_pipeline.run(
                sample.audio_bytes
            )
            generated_transcription = TranscriptionOutput(
                segments=generated_transcription_segments
            )
            logger.info(
                "Generated transcription for {}: {}...",
                sample.uid,
                generated_transcription.text[:50],
            )
            results_manager.save_generated_transcription(
                generated_transcription, sample.uid, self.timestamp
            )
            metrics_pipeline_input = MetricsPipelineInput(
                uid=sample.uid,
                audio_path=sample.audio_path,
                audio_bytes=sample.audio_bytes,
                reference_transcription=sample.reference_transcription,
                generated_transcription=generated_transcription,
            )
            return metrics_pipeline_input
        except Exception as e:
            logger.exception(
                "Error processing {}. Skipping the evaluation for this sample. "
                "The error raised is: {}",
                sample.uid,
                str(e),
            )
            return None

    def run_evaluation(self, output_dir: Path) -> EvaluationSummary:
        """Run the complete evaluation pipeline"""
        results_manager = ResultsManager(output_dir, self.dev)
        metrics_pipeline_inputs: List[MetricsPipelineInput] = []
        for sample in self.inputs:
            metrics_pipeline_input = self.process_single_sample(sample, results_manager)
            if metrics_pipeline_input:
                metrics_pipeline_inputs.append(metrics_pipeline_input)

        if not metrics_pipeline_inputs:
            raise ValueError("No files were successfully processed")

        summary = self.metrics_manager.calculate_and_save_metrics(
            metrics_pipeline_inputs, output_dir
        )

        return summary


class MetricsPipeline:
    """Pipeline to calculate and save evaluation metrics given full EvaluationInputs"""

    def __init__(self) -> None:
        self.dev = os.environ.get("ENV_MODE") == "DEV"
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.metrics_calculator = MetricsCalculator()

    def calculate_metrics(
        self, metrics_pipeline_inputs: List[MetricsPipelineInput]
    ) -> List[EvaluationOutput]:
        """Calculate metrics for all evaluation outputs"""
        if not metrics_pipeline_inputs:
            raise ValueError("No evaluation inputs to process")

        processed_outputs: List[EvaluationOutput] = []
        for sample in metrics_pipeline_inputs:
            metrics = self.metrics_calculator.calculate_metrics(
                sample, sample.generated_transcription
            )

            logger.info(
                "Sample {} - evaluation metrics: {}",
                sample.uid,
                metrics,
            )

            evaluation_output = EvaluationOutput(
                uid=sample.uid,
                reference_transcription=sample.reference_transcription,  # type: ignore[arg-type]
                generated_transcription=sample.generated_transcription,
                metrics=metrics,
            )
            processed_outputs.append(evaluation_output)
        return processed_outputs

    def save_metrics(
        self, evaluation_outputs: List[EvaluationOutput], output_dir: Path
    ) -> EvaluationSummary:
        """Save metrics for all evaluation outputs"""
        if not evaluation_outputs:
            raise ValueError("No evaluation outputs to process")

        results_manager = ResultsManager(output_dir, self.dev)

        wer_scores = [output.metrics.wer for output in evaluation_outputs]
        cer_scores = [output.metrics.cer for output in evaluation_outputs]
        diarization_error_rate_scores = [
            output.metrics.diarization_error_rate for output in evaluation_outputs
        ]
        diarization_coverage_scores = [
            output.metrics.diarization_coverage for output in evaluation_outputs
        ]
        diarization_completeness_scores = [
            output.metrics.diarization_completeness for output in evaluation_outputs
        ]

        summary = EvaluationSummary(
            wer_mean=round(pd.Series(wer_scores).mean(), 4),
            cer_mean=round(pd.Series(cer_scores).mean(), 4),
            der_mean=round(pd.Series(diarization_error_rate_scores).mean(), 4),
            diarization_coverage_mean=float(
                pd.Series(diarization_coverage_scores).mean()
            ),
            diarization_completeness_mean=float(
                pd.Series(diarization_completeness_scores).mean()
            ),
            total_files=len(evaluation_outputs),
        )
        results_manager.save_metrics_csv(evaluation_outputs, self.timestamp)
        results_manager.save_summary_json(summary, self.timestamp)

        df = pd.DataFrame(
            [m.metrics.model_dump() if m.metrics else None for m in evaluation_outputs]
        )

        results_manager.save_results_to_s3(
            df, f"evaluation_results_{self.timestamp}.csv"
        )

        return summary

    def calculate_and_save_metrics(
        self, metrics_pipeline_inputs: List[MetricsPipelineInput], output_dir: Path
    ) -> EvaluationSummary:
        """Calculate and save metrics for all evaluation inputs"""
        evaluation_outputs = self.calculate_metrics(metrics_pipeline_inputs)
        summary = self.save_metrics(evaluation_outputs, output_dir)
        return summary
