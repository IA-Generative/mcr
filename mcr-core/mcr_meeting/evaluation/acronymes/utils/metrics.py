"""Count-aware metrics (TP/FP/TN/FN + precision/recall/accuracy).

For each (audio, acronym) pair we compare the reference count ``expected``
against the transcription count ``predicted``:

    TP = min(expected, predicted)           # correctly emitted occurrences
    FP = max(0, predicted - expected)       # excess / hallucinated occurrences
    FN = max(0, expected - predicted)       # missing occurrences
    TN = 1 if expected == 0 and predicted == 0 else 0

TP/FP/FN are counted in occurrences, so repetitions of an expected acronym
inflate FP (e.g. expected=1, predicted=4 → TP=1, FP=3). TN stays binary (1 per
correctly-absent acronym) because there is no natural upper bound on
"non-repetitions that didn't happen".

Accuracy is the ratio of correct decisions over total decisions under this
mixed counting scheme::

    accuracy = (TP + TN) / (TP + TN + FP + FN)
"""

from mcr_meeting.evaluation.acronymes.types import AcronymMetrics


def score_acronym(expected: int, predicted: int) -> tuple[int, int, int, int]:
    """Count-aware (TP, FP, TN, FN) for one (expected, predicted) pair.

    Examples:

        score_acronym(1, 1)  -> (1, 0, 0, 0)   # correct single emission
        score_acronym(1, 4)  -> (1, 3, 0, 0)   # 3 excess emissions -> FP
        score_acronym(2, 0)  -> (0, 0, 0, 2)   # 2 missing -> FN
        score_acronym(0, 3)  -> (0, 3, 0, 0)   # 3 hallucinations -> FP
        score_acronym(0, 0)  -> (0, 0, 1, 0)   # correctly absent -> TN
    """
    tp = min(expected, predicted)
    fp = max(0, predicted - expected)
    fn = max(0, expected - predicted)
    tn = 1 if expected == 0 and predicted == 0 else 0
    return tp, fp, tn, fn


def _safe_ratio(numerator: int, denominator: int) -> float:
    """Return 0.0 if the denominator is zero, otherwise the ratio."""
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _metrics_from_counts(tp: int, fp: int, tn: int, fn: int) -> AcronymMetrics:
    return AcronymMetrics(
        tp=tp,
        fp=fp,
        tn=tn,
        fn=fn,
        precision=_safe_ratio(tp, tp + fp),
        recall=_safe_ratio(tp, tp + fn),
        accuracy=_safe_ratio(tp + tn, tp + tn + fp + fn),
    )


def compute_audio_metrics(
    expected: dict[str, int],
    predicted: dict[str, int],
) -> AcronymMetrics:
    """Compute TP/FP/TN/FN + precision/recall/accuracy for a single audio.

    Iterates over ``predicted`` keys (the full glossary). Missing keys in
    ``expected`` are treated as 0.
    """
    tp = fp = tn = fn = 0
    for acronym in predicted:
        t, p, n, f = score_acronym(expected.get(acronym, 0), predicted[acronym])
        tp += t
        fp += p
        tn += n
        fn += f
    return _metrics_from_counts(tp, fp, tn, fn)


def compute_global_metrics(
    per_audio_expected: dict[str, dict[str, int]],
    per_audio_predicted: dict[str, dict[str, int]],
) -> AcronymMetrics:
    """Micro-average: sum TP/FP/TN/FN across all audios then recompute ratios."""
    total_tp = total_fp = total_tn = total_fn = 0
    for uid, predicted in per_audio_predicted.items():
        expected = per_audio_expected.get(uid, {})
        m = compute_audio_metrics(expected, predicted)
        total_tp += m.tp
        total_fp += m.fp
        total_tn += m.tn
        total_fn += m.fn
    return _metrics_from_counts(total_tp, total_fp, total_tn, total_fn)
