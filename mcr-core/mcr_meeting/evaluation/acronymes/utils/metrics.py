"""TP / FP / FN / precision / recall computation for acronyms."""

from mcr_meeting.evaluation.acronymes.types import AcronymMetrics


def acronym_tp(count: int) -> int:
    """1 if the acronym is found at least once, 0 otherwise."""
    return 1 if count >= 1 else 0


def acronym_fn(count: int) -> int:
    """1 if the acronym is not found at all, 0 otherwise."""
    return 1 if count == 0 else 0


def acronym_fp(count: int) -> int:
    """Number of excess occurrences: ``max(0, count - 1)``.

    Example: if "ANTS" is found 4 times, we count 1 TP and 3 FP.
    """
    return max(0, count - 1)


def _safe_ratio(numerator: int, denominator: int) -> float:
    """Return 0.0 if the denominator is zero, otherwise the ratio."""
    if denominator == 0:
        return 0.0
    return numerator / denominator


def compute_audio_metrics(counts: dict[str, int]) -> AcronymMetrics:
    """Compute TP/FP/FN/precision/recall for a single audio from its counts."""
    tp = sum(acronym_tp(c) for c in counts.values())
    fp = sum(acronym_fp(c) for c in counts.values())
    fn = sum(acronym_fn(c) for c in counts.values())
    return AcronymMetrics(
        tp=tp,
        fp=fp,
        fn=fn,
        precision=_safe_ratio(tp, tp + fp),
        recall=_safe_ratio(tp, tp + fn),
    )


def compute_global_metrics(
    per_audio_counts: dict[str, dict[str, int]],
) -> AcronymMetrics:
    """Micro-average: sum TP/FP/FN across all audios then recompute
    precision and recall."""
    total_tp = 0
    total_fp = 0
    total_fn = 0
    for counts in per_audio_counts.values():
        m = compute_audio_metrics(counts)
        total_tp += m.tp
        total_fp += m.fp
        total_fn += m.fn
    return AcronymMetrics(
        tp=total_tp,
        fp=total_fp,
        fn=total_fn,
        precision=_safe_ratio(total_tp, total_tp + total_fp),
        recall=_safe_ratio(total_tp, total_tp + total_fn),
    )
