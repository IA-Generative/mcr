"""Compute large transcription chunks from diarization segments."""

from collections.abc import Iterable

from mcr_meeting.app.configs.base import WhisperTranscriptionSettings
from mcr_meeting.app.schemas.transcription_schema import DiarizationSegment, TimeSpan

_settings = WhisperTranscriptionSettings()
MAX_CHUNK_DURATION = _settings.MAX_CHUNK_DURATION
SPLIT_SEARCH_WINDOW_RATIO = _settings.SPLIT_SEARCH_WINDOW_RATIO


def _merge_overlapping_intervals(
    spans: Iterable[TimeSpan],
) -> list[TimeSpan]:
    sorted_spans = sorted(spans, key=lambda s: s.start)
    if not sorted_spans:
        return []

    merged = [sorted_spans[0]]

    for span in sorted_spans[1:]:
        if merged[-1].touches_or_overlaps(span):
            merged[-1] = merged[-1].merge(span)
        else:
            merged.append(span)

    return merged


def _find_split_boundary(
    chunk_start: float,
    chunk_intervals: list[TimeSpan],
    next_interval: TimeSpan,
    max_chunk_duration: float,
    split_search_window_ratio: float = SPLIT_SEARCH_WINDOW_RATIO,
) -> float:
    window_start = chunk_start + (1 - split_search_window_ratio) * max_chunk_duration
    window_end = chunk_start + max_chunk_duration

    all_intervals = chunk_intervals + [next_interval]

    best_gap: TimeSpan | None = None

    for j in range(len(all_intervals) - 1):
        gap = all_intervals[j].gap_to(all_intervals[j + 1])
        if gap is None or gap.start < window_start:
            continue
        if gap.midpoint > window_end:
            continue

        if best_gap is None or gap.duration > best_gap.duration:
            best_gap = gap

    if best_gap is not None:
        return best_gap.midpoint

    return window_end


def compute_transcription_chunks(
    diarization: list[DiarizationSegment],
    max_chunk_duration: float = MAX_CHUNK_DURATION,
) -> list[TimeSpan]:
    if not diarization:
        return []

    spans = (TimeSpan(seg.start, seg.end) for seg in diarization)
    merged = _merge_overlapping_intervals(spans)

    if not merged:
        return []

    chunks: list[TimeSpan] = []
    chunk_start = merged[0].start
    chunk_intervals: list[TimeSpan] = [merged[0]]

    for i in range(1, len(merged)):
        interval = merged[i]
        prospective_end = interval.end
        prospective_duration = prospective_end - chunk_start

        if prospective_duration <= max_chunk_duration:
            chunk_intervals.append(interval)
            continue

        boundary = _find_split_boundary(
            chunk_start, chunk_intervals, interval, max_chunk_duration
        )

        chunks.append(TimeSpan(chunk_start, boundary))
        chunk_start = boundary
        chunk_intervals = [interval]

    last_end = chunk_intervals[-1].end
    chunks.append(TimeSpan(chunk_start, last_end))

    return chunks
