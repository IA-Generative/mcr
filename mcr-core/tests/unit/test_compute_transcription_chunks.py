"""Unit tests for compute_transcription_chunks."""

from mcr_meeting.app.services.speech_to_text.types import DiarizationSegment
from mcr_meeting.app.services.speech_to_text.utils.chunking import (
    MAX_CHUNK_DURATION,
    compute_transcription_chunks,
)
from mcr_meeting.app.services.speech_to_text.utils.types import TimeSpan


def _seg(start: float, end: float, speaker: str = "S1") -> DiarizationSegment:
    return DiarizationSegment(start=start, end=end, speaker=speaker)


class TestEmptyInput:
    def test_empty_list_returns_empty(self):
        assert compute_transcription_chunks([]) == []


class TestSingleSegment:
    def test_single_short_segment(self):
        result = compute_transcription_chunks([_seg(1.0, 5.0)])
        assert result == [TimeSpan(1.0, 5.0)]

    def test_single_segment_exactly_max_duration(self):
        result = compute_transcription_chunks(
            [_seg(0.0, MAX_CHUNK_DURATION)], max_chunk_duration=MAX_CHUNK_DURATION
        )
        assert result == [TimeSpan(0.0, MAX_CHUNK_DURATION)]


class TestAllSegmentsFitInOneChunk:
    def test_multiple_segments_under_max(self):
        segments = [
            _seg(0.0, 3.0),
            _seg(4.0, 6.0),
            _seg(7.0, 10.0),
            _seg(11.0, 13.0),
        ]
        result = compute_transcription_chunks(segments, max_chunk_duration=600.0)
        assert len(result) == 1
        assert result[0] == TimeSpan(0.0, 13.0)


class TestOverlappingSegments:
    def test_overlapping_segments_are_merged(self):
        segments = [
            _seg(0.0, 10.0, "S1"),
            _seg(3.0, 6.0, "S2"),
            _seg(7.0, 9.0, "S3"),
        ]
        result = compute_transcription_chunks(segments, max_chunk_duration=600.0)
        assert len(result) == 1
        assert result[0] == TimeSpan(0.0, 10.0)

    def test_partially_overlapping_extends_end(self):
        segments = [
            _seg(0.0, 5.0),
            _seg(4.0, 8.0),
            _seg(10.0, 12.0),
        ]
        result = compute_transcription_chunks(segments, max_chunk_duration=600.0)
        assert len(result) == 1
        assert result[0] == TimeSpan(0.0, 12.0)


class TestSplitRequired:
    def test_split_at_largest_silence_in_last_20_percent(self):
        """Segments that exceed max_chunk_duration should split at the largest
        silence in the last 20% of the chunk."""
        # max = 100s, last 20% window = [80, 100]
        segments = [
            _seg(0.0, 50.0),
            _seg(51.0, 80.0),  # gap at 80-85 is in last 20%
            _seg(85.0, 95.0),  # gap at 95-96 is in last 20%
            _seg(96.0, 110.0),
        ]
        result = compute_transcription_chunks(segments, max_chunk_duration=100.0)
        assert len(result) == 2
        # Largest gap in [80, 100] is 80.0→85.0 (5s) — boundary at midpoint 82.5
        assert result[0].end == 82.5
        assert result[1].start == 82.5

    def test_split_hard_cut_when_gap_outside_window(self):
        """When no gap is inside the search window, hard cut at max_chunk_duration."""
        # max = 20s, search window = [16, 20]
        # Only gap is at 10-11 (outside window)
        segments = [
            _seg(0.0, 10.0),
            _seg(11.0, 25.0),
        ]
        result = compute_transcription_chunks(segments, max_chunk_duration=20.0)
        assert len(result) == 2
        assert result[0].end == 20.0  # hard cut at chunk_start + max
        assert result[1].start == 20.0


class TestLongIndividualSegment:
    def test_single_segment_exceeding_max_kept_as_one_chunk(self):
        """A single continuous segment > max_chunk_duration stays as one chunk
        (no internal split — Whisper's VAD handles it)."""
        segments = [_seg(0.0, 700.0)]
        result = compute_transcription_chunks(segments, max_chunk_duration=600.0)
        assert len(result) == 1
        assert result[0] == TimeSpan(0.0, 700.0)

    def test_very_long_single_segment_kept_as_one_chunk(self):
        segments = [_seg(0.0, 2000.0)]
        result = compute_transcription_chunks(segments, max_chunk_duration=600.0)
        assert len(result) == 1
        assert result[0] == TimeSpan(0.0, 2000.0)


class TestEdgeCases:
    def test_segments_exactly_at_max_duration(self):
        """Segments totaling exactly max_chunk_duration should be one chunk."""
        segments = [
            _seg(0.0, 50.0),
            _seg(50.0, 100.0),
        ]
        result = compute_transcription_chunks(segments, max_chunk_duration=100.0)
        assert len(result) == 1
        assert result[0] == TimeSpan(0.0, 100.0)

    def test_many_small_segments(self):
        """Many small segments that all fit in one chunk."""
        segments = [_seg(i * 2.0, i * 2.0 + 1.0) for i in range(100)]
        result = compute_transcription_chunks(segments, max_chunk_duration=600.0)
        assert len(result) == 1
        assert result[0].start == 0.0
        assert result[0].end == 199.0

    def test_unsorted_segments(self):
        """Segments not sorted by start should still work."""
        segments = [
            _seg(10.0, 15.0),
            _seg(0.0, 5.0),
            _seg(6.0, 8.0),
        ]
        result = compute_transcription_chunks(segments, max_chunk_duration=600.0)
        assert len(result) == 1
        assert result[0] == TimeSpan(0.0, 15.0)

    def test_multiple_chunks_correct_coverage(self):
        """Verify that multiple chunks together cover the full range."""
        # Build segments that span ~1500s with gaps
        segments = []
        for i in range(15):
            start = i * 100.0
            segments.append(_seg(start, start + 90.0))
        result = compute_transcription_chunks(segments, max_chunk_duration=600.0)
        # All original speech should be covered
        assert result[0].start == 0.0
        assert result[-1].end == 1490.0
        # Chunks should be contiguous (no overlap or gap)
        for i in range(len(result) - 1):
            assert result[i].end == result[i + 1].start
