from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment
from mcr_meeting.evaluation.asr_evaluation_pipeline import (
    ASREvaluationPipeline,
    MetricsPipeline,
)
from mcr_meeting.evaluation.eval_types import (
    EvaluationInput,
    EvaluationMetrics,
    EvaluationOutput,
    EvaluationSummary,
    MetricsPipelineInput,
    TranscriptionOutput,
)


@pytest.fixture
def mock_segments():
    return [
        DiarizedTranscriptionSegment(
            id=1, start=0.0, end=1.0, text="Hello world", speaker="SPEAKER_00"
        )
    ]


@pytest.fixture
def mock_transcription(mock_segments):
    return TranscriptionOutput(segments=mock_segments)


@pytest.fixture
def mock_evaluation_input(mock_transcription):
    return EvaluationInput(
        uid="test_uid",
        audio_path=Path("/fake/path.wav"),
        audio_bytes=BytesIO(b"fake_audio"),
        reference_transcription=mock_transcription,
    )


@pytest.fixture
def mock_metrics():
    return EvaluationMetrics(
        uid="test_uid",
        wer=0.1,
        cer=0.05,
        diarization_error_rate=0.2,
        diarization_coverage=0.9,
        diarization_completeness=0.85,
    )


@pytest.fixture
def mock_evaluation_output(mock_transcription, mock_metrics):
    return EvaluationOutput(
        uid="test_uid",
        reference_transcription=mock_transcription,
        generated_transcription=mock_transcription,
        metrics=mock_metrics,
    )


class TestASREvaluationPipeline:
    @patch("mcr_meeting.evaluation.asr_evaluation_pipeline.SpeechToTextPipeline")
    @patch("mcr_meeting.evaluation.asr_evaluation_pipeline.MetricsPipeline")
    def test_init(
        self, mock_metrics_pipeline, mock_stt_pipeline, mock_evaluation_input
    ):
        pipeline = ASREvaluationPipeline([mock_evaluation_input])

        assert pipeline.inputs == [mock_evaluation_input]
        assert pipeline.timestamp is not None
        mock_stt_pipeline.assert_called_once()
        mock_metrics_pipeline.assert_called_once()

    @patch("mcr_meeting.evaluation.asr_evaluation_pipeline.SpeechToTextPipeline")
    @patch("mcr_meeting.evaluation.asr_evaluation_pipeline.MetricsPipeline")
    def test_process_single_sample_success(
        self,
        mock_metrics_pipeline,
        mock_stt_pipeline,
        mock_evaluation_input,
        mock_segments,
    ):
        mock_stt_instance = Mock()
        mock_stt_instance.run.return_value = mock_segments
        mock_stt_pipeline.return_value = mock_stt_instance

        pipeline = ASREvaluationPipeline([mock_evaluation_input])
        results_manager = Mock()

        result = pipeline.process_single_sample(mock_evaluation_input, results_manager)

        assert result is not None
        assert result.uid == "test_uid"
        assert result.generated_transcription == TranscriptionOutput(
            segments=mock_segments
        )
        mock_stt_instance.run.assert_called_once()
        results_manager.save_generated_transcription.assert_called_once()

    @patch("mcr_meeting.evaluation.asr_evaluation_pipeline.SpeechToTextPipeline")
    @patch("mcr_meeting.evaluation.asr_evaluation_pipeline.MetricsPipeline")
    def test_process_single_sample_exception(
        self, mock_metrics_pipeline, mock_stt_pipeline, mock_evaluation_input
    ):
        mock_stt_instance = Mock()
        mock_stt_instance.run.side_effect = Exception("Processing error")
        mock_stt_pipeline.return_value = mock_stt_instance

        pipeline = ASREvaluationPipeline([mock_evaluation_input])
        results_manager = Mock()

        result = pipeline.process_single_sample(mock_evaluation_input, results_manager)

        assert result is None

    @patch("mcr_meeting.evaluation.asr_evaluation_pipeline.SpeechToTextPipeline")
    @patch("mcr_meeting.evaluation.asr_evaluation_pipeline.MetricsPipeline")
    @patch("mcr_meeting.evaluation.asr_evaluation_pipeline.ResultsManager")
    def test_run_evaluation_success(
        self,
        mock_results_manager,
        mock_metrics_pipeline_cls,
        mock_stt_pipeline,
        mock_evaluation_input,
        mock_segments,
    ):
        mock_stt_instance = Mock()
        mock_stt_instance.run.return_value = mock_segments
        mock_stt_pipeline.return_value = mock_stt_instance

        mock_metrics_instance = Mock()
        expected_summary = EvaluationSummary(
            wer_mean=0.1,
            cer_mean=0.05,
            der_mean=0.2,
            diarization_coverage_mean=0.9,
            diarization_completeness_mean=0.85,
            total_files=1,
        )
        mock_metrics_instance.calculate_and_save_metrics.return_value = expected_summary
        mock_metrics_pipeline_cls.return_value = mock_metrics_instance

        mock_rm_instance = Mock()
        mock_results_manager.return_value = mock_rm_instance

        pipeline = ASREvaluationPipeline([mock_evaluation_input])
        summary = pipeline.run_evaluation(Path("/output"))

        assert summary == expected_summary
        mock_metrics_instance.calculate_and_save_metrics.assert_called_once()

    @patch("mcr_meeting.evaluation.asr_evaluation_pipeline.SpeechToTextPipeline")
    @patch("mcr_meeting.evaluation.asr_evaluation_pipeline.MetricsPipeline")
    @patch("mcr_meeting.evaluation.asr_evaluation_pipeline.ResultsManager")
    def test_run_evaluation_no_successful_processing(
        self,
        mock_results_manager,
        mock_metrics_pipeline,
        mock_stt_pipeline,
        mock_evaluation_input,
    ):
        mock_evaluation_input.audio_bytes = None
        pipeline = ASREvaluationPipeline([mock_evaluation_input])

        with pytest.raises(ValueError, match="No files were successfully processed"):
            pipeline.run_evaluation(Path("/output"))


class TestMetricsPipeline:
    @patch("mcr_meeting.evaluation.asr_evaluation_pipeline.MetricsCalculator")
    def test_init(self, mock_metrics_calculator):
        pipeline = MetricsPipeline()

        assert pipeline.timestamp is not None
        mock_metrics_calculator.assert_called_once()

    @patch("mcr_meeting.evaluation.asr_evaluation_pipeline.MetricsCalculator")
    def test_calculate_metrics_success(
        self, mock_metrics_calculator, mock_transcription, mock_metrics
    ):
        mock_calc_instance = Mock()
        mock_calc_instance.calculate_metrics.return_value = mock_metrics
        mock_metrics_calculator.return_value = mock_calc_instance

        pipeline = MetricsPipeline()

        metrics_input = MetricsPipelineInput(
            uid="test_uid",
            audio_path=Path("/fake/path.wav"),
            audio_bytes=BytesIO(b"fake"),
            reference_transcription=mock_transcription,
            generated_transcription=mock_transcription,
        )

        outputs = pipeline.calculate_metrics([metrics_input])

        assert len(outputs) == 1
        assert outputs[0].uid == "test_uid"
        assert outputs[0].metrics == mock_metrics

    @patch("mcr_meeting.evaluation.asr_evaluation_pipeline.MetricsCalculator")
    def test_calculate_metrics_empty_inputs(self, mock_metrics_calculator):
        pipeline = MetricsPipeline()
        with pytest.raises(ValueError, match="No evaluation inputs to process"):
            pipeline.calculate_metrics([])

    @patch("mcr_meeting.evaluation.asr_evaluation_pipeline.MetricsCalculator")
    @patch("mcr_meeting.evaluation.asr_evaluation_pipeline.ResultsManager")
    def test_save_metrics_success(
        self, mock_results_manager, mock_metrics_calculator, mock_evaluation_output
    ):
        mock_rm_instance = Mock()
        mock_results_manager.return_value = mock_rm_instance

        pipeline = MetricsPipeline()
        summary = pipeline.save_metrics([mock_evaluation_output], Path("/output"))

        assert summary.total_files == 1
        assert 0 <= summary.wer_mean <= 1
        assert 0 <= summary.cer_mean <= 1
        mock_rm_instance.save_metrics_csv.assert_called_once()
        mock_rm_instance.save_summary_json.assert_called_once()
        mock_rm_instance.save_results_to_s3.assert_called_once()

    @patch("mcr_meeting.evaluation.asr_evaluation_pipeline.MetricsCalculator")
    def test_save_metrics_empty_outputs(self, mock_metrics_calculator):
        pipeline = MetricsPipeline()

        with pytest.raises(ValueError, match="No evaluation outputs to process"):
            pipeline.save_metrics([], Path("/output"))

    @patch("mcr_meeting.evaluation.asr_evaluation_pipeline.MetricsCalculator")
    @patch("mcr_meeting.evaluation.asr_evaluation_pipeline.ResultsManager")
    def test_calculate_and_save_metrics(
        self,
        mock_results_manager,
        mock_metrics_calculator,
        mock_transcription,
        mock_metrics,
    ):
        mock_calc_instance = Mock()
        mock_calc_instance.calculate_metrics.return_value = mock_metrics
        mock_metrics_calculator.return_value = mock_calc_instance

        mock_rm_instance = Mock()
        mock_results_manager.return_value = mock_rm_instance

        pipeline = MetricsPipeline()

        metrics_input = MetricsPipelineInput(
            uid="test_uid",
            audio_path=Path("/fake/path.wav"),
            audio_bytes=BytesIO(b"fake"),
            reference_transcription=mock_transcription,
            generated_transcription=mock_transcription,
        )

        summary = pipeline.calculate_and_save_metrics([metrics_input], Path("/output"))

        assert summary.total_files == 1
        mock_rm_instance.save_metrics_csv.assert_called_once()
        mock_rm_instance.save_summary_json.assert_called_once()
