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
from mcr_meeting.evaluation.eval_types import (
    DiarizationMetrics,
    EvaluationMetrics,
    MetricsPipelineInput,
    TranscriptionMetrics,
    TranscriptionOutput,
)
from mcr_meeting.evaluation.utils.text_normalization import french_text_normalizer


class MetricsCalculator:
    """Handles calculation of evaluation metrics"""

    @staticmethod
    def calculate_transcription_metrics(
        reference_text: str,
        hypothesis_text: str,
    ) -> TranscriptionMetrics:
        """Calculate WER and CER metrics for a single file

        Both reference and hypothesis texts are normalized before metric computation
        using the `french_text_normalizer` function.

        We remove consecutive duplicate words from the reference text but not from the hypothesis text,
        since ASR systems may produce such repetitions as a common type of error (e.g. "le le", "de de de")
        and we want to ensure that these are counted as errors rather than being normalized away in both texts.
        """
        normalized_reference_text = french_text_normalizer(
            reference_text, remove_repetitions=True
        )
        normalized_hypothesis_text = french_text_normalizer(
            hypothesis_text, remove_repetitions=False
        )
        wer_score = wer(normalized_reference_text, normalized_hypothesis_text)
        cer_score = cer(normalized_reference_text, normalized_hypothesis_text)
        return TranscriptionMetrics(wer=round(wer_score, 4), cer=round(cer_score, 4))

    @staticmethod
    def calculate_diarization_metrics(
        reference_segments: list[DiarizedTranscriptionSegment],
        hypothesis_segments: list[DiarizedTranscriptionSegment],
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
        sample: MetricsPipelineInput,
        hypothesis_transcription: TranscriptionOutput,
    ) -> EvaluationMetrics:
        """Calculate metrics for a single file"""
        logger.info("Calculating metrics for {}", sample.uid)
        transcription_metrics = self.calculate_transcription_metrics(
            reference_text=sample.reference_transcription.text,
            hypothesis_text=hypothesis_transcription.text,
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
