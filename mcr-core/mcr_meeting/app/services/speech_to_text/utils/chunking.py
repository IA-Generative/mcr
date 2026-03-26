"""Compute large transcription chunks from diarization segments."""

from mcr_meeting.app.configs.base import WhisperTranscriptionSettings
from mcr_meeting.app.services.speech_to_text.types import DiarizationSegment
from mcr_meeting.app.services.speech_to_text.utils.types import TimeSpan

_settings = WhisperTranscriptionSettings()
MAX_CHUNK_DURATION = _settings.MAX_CHUNK_DURATION
SPLIT_SEARCH_WINDOW_RATIO = _settings.SPLIT_SEARCH_WINDOW_RATIO


def _merge_overlapping_intervals(
    segments: list[DiarizationSegment],
) -> list[TimeSpan]:
    """Merge overlapping diarization segments into non-overlapping TimeSpans."""
    if not segments:
        return []

    sorted_segments = sorted(segments, key=lambda s: s.start)
    merged = [TimeSpan(sorted_segments[0].start, sorted_segments[0].end)]

    for seg in sorted_segments[1:]:
        if seg.start <= merged[-1].end:
            merged[-1] = TimeSpan(merged[-1].start, max(merged[-1].end, seg.end))
        else:
            merged.append(TimeSpan(seg.start, seg.end))

    return merged


def _find_split_boundary(
    chunk_start: float,
    chunk_intervals: list[TimeSpan],
    next_interval: TimeSpan,
    max_chunk_duration: float,
    split_search_window_ratio: float = SPLIT_SEARCH_WINDOW_RATIO,
) -> float:
    """Find the best boundary to split a chunk that would exceed max duration.

    Looks for the largest silence gap in the last ``split_search_window_ratio``
    of the chunk. Falls back to the last available gap, or an arbitrary cut at
    max_chunk_duration.
    """
    window_start = chunk_start + (1 - split_search_window_ratio) * max_chunk_duration
    window_end = chunk_start + max_chunk_duration

    all_intervals = chunk_intervals + [next_interval]

    # Collect all silences (gaps between consecutive intervals)
    best_gap_mid: float | None = None
    best_gap_size = 0.0

    for j in range(len(all_intervals) - 1):
        gap_start = all_intervals[j].end
        if gap_start < window_start:
            continue
        gap_end = all_intervals[j + 1].start
        gap_size = gap_end - gap_start
        gap_mid = (gap_start + gap_end) / 2.0
        if gap_mid > window_end:
            continue

        if gap_size > best_gap_size:
            best_gap_size = gap_size
            best_gap_mid = gap_mid

    if best_gap_mid is not None:
        return best_gap_mid

    # No gap at all — hard cut
    return window_end


def compute_transcription_chunks(
    diarization: list[DiarizationSegment],
    max_chunk_duration: float = MAX_CHUNK_DURATION,
) -> list[TimeSpan]:
    """Compute large transcription chunks from diarization segments.

    Merges overlapping diarization segments, then greedily accumulates them
    into chunks up to ``max_chunk_duration``. When a chunk would exceed the
    limit, the boundary is placed at the midpoint of the largest silence in
    the last portion (controlled by ``split_search_window_ratio``) of the chunk.

    Args:
        diarization: Diarization segments (may overlap).
        max_chunk_duration: Maximum chunk length in seconds (default 600).

    Returns:
        List of TimeSpan chunks covering all speech regions.
    """
    if not diarization:
        return []

    merged = _merge_overlapping_intervals(diarization)

    if not merged:
        return []

    # Greedy accumulation
    chunks: list[TimeSpan] = []
    chunk_start = merged[0].start
    # Track the intervals belonging to the current chunk
    chunk_intervals: list[TimeSpan] = [merged[0]]

    for i in range(1, len(merged)):
        interval = merged[i]
        prospective_end = interval.end
        prospective_duration = prospective_end - chunk_start

        if prospective_duration <= max_chunk_duration:
            chunk_intervals.append(interval)
            continue

        # Need to split: find the best silence in the search window
        boundary = _find_split_boundary(
            chunk_start, chunk_intervals, interval, max_chunk_duration
        )

        chunks.append(TimeSpan(chunk_start, boundary))
        chunk_start = boundary
        chunk_intervals = [interval]

    # Final chunk
    last_end = chunk_intervals[-1].end
    chunks.append(TimeSpan(chunk_start, last_end))

    return chunks
