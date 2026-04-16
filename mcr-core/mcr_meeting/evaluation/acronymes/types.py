from pydantic import BaseModel


class AcronymMetrics(BaseModel):
    """Count-aware classification metrics for an audio or aggregated globally.

    For each (audio, acronym) pair with reference count ``expected`` and
    transcription count ``predicted`` (see ``score_acronym``)::

        TP = min(expected, predicted)
        FP = max(0, predicted - expected)     # excess / hallucinated occurrences
        FN = max(0, expected - predicted)     # missing occurrences
        TN = 1 if expected == 0 and predicted == 0 else 0
    """

    tp: int
    fp: int
    tn: int
    fn: int
    precision: float
    recall: float
    accuracy: float


class AcronymPerAudioEntry(BaseModel):
    """Per-audio detail included in the final summary."""

    expected: dict[str, int]
    predicted: dict[str, int]
    metrics: AcronymMetrics


class AcronymEvaluationSummary(BaseModel):
    """Global summary of an acronym evaluation run."""

    total_files: int
    per_audio: dict[str, AcronymPerAudioEntry]
    global_metrics: AcronymMetrics
    aggregate_expected: dict[str, int]
    aggregate_predicted: dict[str, int]
