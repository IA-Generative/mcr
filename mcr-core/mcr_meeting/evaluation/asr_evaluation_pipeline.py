import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd
from loguru import logger

from mcr_meeting.evaluation.eval_types import (
    EvaluationInput,
    EvaluationOutput,
    EvaluationSummary,
)
from mcr_meeting.evaluation.utils import (
    AudioFileProcessor,
    MetricsCalculator,
    ResultsManager,
)


class ASREvaluationPipeline:
    """Main pipeline orchestrator for Automatic Speech Recognition (ASR) evaluation"""

    def __init__(self, inputs: List[EvaluationInput], model: Optional[object] = None):
        self.inputs = inputs
        self.dev = os.environ.get("ENV_MODE") == "DEV"
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.audio_processor = AudioFileProcessor(model)
        self.metrics_manager = MetricsPipeline()

    def process_single_sample(
        self, sample: EvaluationInput, results_manager: ResultsManager
    ) -> Optional[EvaluationInput]:
        """Process a single audio file and return evaluation metrics"""
        try:
            logger.info("Processing sample {}...", sample.uid)

            if not sample.audio_bytes:
                logger.warning(
                    "Empty audio file, skipping sample %s",
                    sample.uid,
                )
                return None

            generated_transcription = self.audio_processor.process_audio_file(
                sample.audio_bytes
            )
            logger.info(
                "Generated transcription for {}: {}...",
                sample.uid,
                generated_transcription.text[:50],
            )
            results_manager.save_generated_transcription(
                generated_transcription, sample.uid, self.timestamp
            )
            sample.generated_transcription = generated_transcription
            return sample
        except Exception as e:
            logger.error("Error processing {}: {}", sample.uid, str(e))
            return None

    def run_evaluation(self, output_dir: Path) -> EvaluationSummary:
        """Run the complete evaluation pipeline"""
        results_manager = ResultsManager(output_dir, self.dev)
        evaluation_inputs: List[EvaluationInput] = []
        for sample in self.inputs:
            evaluation_input = self.process_single_sample(sample, results_manager)
            if evaluation_input:
                evaluation_inputs.append(evaluation_input)

        if not evaluation_inputs:
            raise ValueError("No files were successfully processed")

        summary = self.metrics_manager.calculate_and_save_metrics(
            evaluation_inputs, output_dir
        )

        return summary


class MetricsPipeline:
    """Pipeline to calculate and save evaluation metrics given full EvaluationInputs"""

    def __init__(self) -> None:
        self.dev = os.environ.get("ENV_MODE") == "DEV"
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.metrics_calculator = MetricsCalculator()

    def calculate_metrics(
        self, evaluation_inputs: List[EvaluationInput]
    ) -> List[EvaluationOutput]:
        """Calculate metrics for all evaluation outputs"""
        processed_outputs: List[EvaluationOutput] = []
        for sample in evaluation_inputs:
            if not sample.generated_transcription:
                logger.warning(
                    "No generated transcription for sample {}, skipping.",
                    sample.uid,
                )
                continue

            metrics = self.metrics_calculator.calculate_metrics(
                sample, sample.generated_transcription
            )

            if not metrics:
                logger.warning(
                    "Metrics could not be calculated for sample {}, skipping.",
                    sample.uid,
                )
                continue

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
        if not evaluation_outputs:
            raise ValueError("No files were successfully processed")

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
        self, evaluation_inputs: List[EvaluationInput], output_dir: Path
    ) -> EvaluationSummary:
        """Calculate and save metrics for all evaluation inputs"""
        evaluation_outputs = self.calculate_metrics(evaluation_inputs)
        summary = self.save_metrics(evaluation_outputs, output_dir)
        return summary
