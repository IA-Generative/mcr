from pydantic import BaseModel


class AcronymMetrics(BaseModel):
    """TP/FP/FN + precision and recall — per audio or aggregated globally."""

    tp: int
    fp: int
    fn: int
    precision: float
    recall: float


class AcronymPerAudioEntry(BaseModel):
    """Per-audio detail included in the final summary."""

    counts: dict[str, int]
    metrics: AcronymMetrics


class AcronymEvaluationSummary(BaseModel):
    """Global summary of an acronym evaluation run."""

    total_files: int
    per_audio: dict[str, AcronymPerAudioEntry]
    global_metrics: AcronymMetrics
    aggregate_counts: dict[str, int]
