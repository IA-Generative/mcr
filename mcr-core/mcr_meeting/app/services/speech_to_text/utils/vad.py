"""Utility functions for processing audio and transcription segments during Speech To Text pipeline."""

import re
from typing import List, Optional, Tuple

from loguru import logger

from mcr_meeting.app.configs.base import VADSettings
from mcr_meeting.app.schemas.transcription_schema import TranscriptionSegment
from mcr_meeting.app.services.speech_to_text.types import DiarizationSegment
from mcr_meeting.app.services.speech_to_text.utils.types import TimeSpan

vad_settings = VADSettings()


def get_vad_segments_from_diarization(
    diarization: List[DiarizationSegment],
) -> List[DiarizationSegment]:
    """Filter diarization segments using VAD parameters to remove short segments and merge close ones.

    Args:
        diarization (List[DiarizationSegment]): List of diarization segments.

    Returns:
        List[DiarizationSegment]: Filtered list of diarization segments.
    """
    vad_segments = []
    for segment in diarization:
        if segment.end - segment.start > vad_settings.MIN_SPEECH_DURATION:
            vad_segments.append(segment)

    if not vad_segments:
        return []
    merged_segments = [vad_segments[0]]
    for current in vad_segments[1:]:
        previous = merged_segments[-1]
        if current.start - previous.end <= vad_settings.MAX_SILENCE_GAP:
            merged_segments[-1] = DiarizationSegment(
                start=previous.start,
                end=max(previous.end, current.end),
                speaker=previous.speaker,
            )
        else:
            merged_segments.append(current)
    total_voiced_duration = sum(seg.end - seg.start for seg in merged_segments)
    logger.info("Total voiced duration after VAD filtering: {}", total_voiced_duration)

    return merged_segments


def find_best_matching_diarization(
    transcription_span: TimeSpan,
    diarization_spans: List[Tuple[TimeSpan, DiarizationSegment]],
) -> Tuple[Optional[DiarizationSegment], float]:
    """Find the diarization segment with the maximum overlap (seconds) with
    a given transcription span.

    Returns a tuple of (best_matching_diarization_segment|None, overlap_seconds).
    """
    best: Optional[DiarizationSegment] = None
    max_overlap_seconds = 0.0
    for span, diarization_segment in diarization_spans:
        overlap_seconds = transcription_span.overlap(span)
        if overlap_seconds > max_overlap_seconds:
            max_overlap_seconds = overlap_seconds
            best = diarization_segment
    return best, max_overlap_seconds


def transcription_span_outside_diarization_range(
    transcription_span: TimeSpan, diarization_range: TimeSpan
) -> bool:
    """Return True when the transcription span is completely outside the
    diarization range (no possible overlap).
    """
    outside = (
        transcription_span.end < diarization_range.start
        or transcription_span.start > diarization_range.end
    )
    if outside:
        logger.warning(
            "Transcription segment is outside the diarization range: start={}, end={}",
            transcription_span.start,
            transcription_span.end,
        )
    return outside


def diarize_vad_transcription_segments(
    vad_transcription_segments: List[TranscriptionSegment],
    diarization_result: List[DiarizationSegment],
) -> List[TranscriptionSegment]:
    """Align VAD transcription segments with diarization results to assign speaker labels.

    This implementation uses the TimeSpan helper to make overlap/containment
    reasoning concise and self-documenting.
    """
    aligned_segments: List[TranscriptionSegment] = []

    if not diarization_result:
        logger.warning("Diarization result is empty, returning empty speakers.")
        empty_speaker_transcription_segments = [
            TranscriptionSegment(
                id=segment.id,
                start=segment.start,
                end=segment.end,
                text=segment.text,
                speaker="",
            )
            for segment in vad_transcription_segments
        ]
        return empty_speaker_transcription_segments

    diarization_spans = [(TimeSpan(d.start, d.end), d) for d in diarization_result]
    diarization_range = TimeSpan(
        diarization_result[0].start, diarization_result[-1].end
    )

    logger.info(
        "Diarization segments range: start={} to end={}",
        diarization_range.start,
        diarization_range.end,
    )

    for transcription_segment in vad_transcription_segments:
        transcription_span = TimeSpan(
            transcription_segment.start, transcription_segment.end
        )

        if transcription_span_outside_diarization_range(
            transcription_span, diarization_range
        ):
            continue

        best_matching_diarization, max_overlap_seconds = find_best_matching_diarization(
            transcription_span, diarization_spans
        )

        if best_matching_diarization and max_overlap_seconds > 0:
            aligned_segments.append(
                TranscriptionSegment(
                    id=transcription_segment.id,
                    start=transcription_segment.start,
                    end=transcription_segment.end,
                    text=transcription_segment.text,
                    speaker=best_matching_diarization.speaker,
                )
            )
        else:
            logger.info(
                "No matching diarization segment found for transcription segment: start={}, end={}",
                transcription_segment.start,
                transcription_segment.end,
            )

    return aligned_segments


def convert_to_french_speaker(speaker_label: str) -> str:
    """Convert speaker labels to French format"""
    return re.sub(r"SPEAKER_(\d+)", r"LOCUTEUR_\1", speaker_label)
