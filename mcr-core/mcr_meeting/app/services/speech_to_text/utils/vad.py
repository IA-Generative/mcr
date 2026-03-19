"""Utility functions for processing audio and transcription segments during Speech To Text pipeline."""

import re

from loguru import logger

from mcr_meeting.app.configs.base import VADSettings
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
    TranscriptionSegment,
)
from mcr_meeting.app.services.speech_to_text.types import DiarizationSegment
from mcr_meeting.app.services.speech_to_text.utils.types import TimeSpan

vad_settings = VADSettings()


def get_vad_segments_from_diarization(
    diarization: list[DiarizationSegment],
) -> list[TimeSpan]:
    """Filter diarization segments using VAD parameters to remove short segments and merge close ones.

    Args:
        diarization (List[DiarizationSegment]): List of diarization segments.

    Returns:
        List[TimeSpan]: Filtered list of time spans (start/end only).
    """
    vad_segments = []
    for segment in diarization:
        if segment.end - segment.start > vad_settings.MIN_SPEECH_DURATION:
            vad_segments.append(segment)

    if not vad_segments:
        return []
    span_list = [TimeSpan(vad_segments[0].start, vad_segments[0].end)]
    for segment in vad_segments[1:]:
        current = TimeSpan(segment.start, segment.end)
        previous = span_list[-1]
        if current.start - previous.end <= vad_settings.MAX_SILENCE_GAP:
            span_list[-1] = TimeSpan(
                start=previous.start,
                end=max(previous.end, current.end),
            )
        else:
            span_list.append(current)
    total_voiced_duration = sum(span.end - span.start for span in span_list)
    logger.debug("Total voiced duration after VAD filtering: {}", total_voiced_duration)

    return span_list


def find_best_matching_diarization(
    transcription_span: TimeSpan,
    diarization_spans: list[tuple[TimeSpan, DiarizationSegment]],
) -> tuple[DiarizationSegment | None, float]:
    """Find the diarization segment with the maximum overlap (seconds) with
    a given transcription span.

    Returns a tuple of (best_matching_diarization_segment|None, overlap_seconds).
    """
    best: DiarizationSegment | None = None
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
    vad_transcription_segments: list[TranscriptionSegment],
    diarization_result: list[DiarizationSegment],
) -> list[DiarizedTranscriptionSegment]:
    """Align VAD transcription segments with diarization results to assign speaker labels.

    This implementation uses the TimeSpan helper to make overlap/containment
    reasoning concise and self-documenting.
    """
    aligned_segments: list[DiarizedTranscriptionSegment] = []

    if not diarization_result:
        logger.warning("Diarization result is empty, returning empty speakers.")
        empty_speaker_transcription_segments = [
            DiarizedTranscriptionSegment(
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

    logger.debug(
        "Matching transcription against diarization segments in the range: start={} to end={}",
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
            if best_matching_diarization.speaker:
                speaker = best_matching_diarization.speaker
            else:
                speaker = f"INCONNU_{transcription_segment.id}"
            aligned_segments.append(
                DiarizedTranscriptionSegment(
                    id=transcription_segment.id,
                    start=transcription_segment.start,
                    end=transcription_segment.end,
                    text=transcription_segment.text,
                    speaker=speaker,
                )
            )
        else:
            logger.debug(
                "No matching diarization segment found for transcription segment: start={}, end={}",
                transcription_segment.start,
                transcription_segment.end,
            )

    return aligned_segments


def convert_to_french_speaker(speaker_label: str) -> str:
    """Convert speaker labels to French format"""
    return re.sub(r"SPEAKER_(\d+)", r"LOCUTEUR_\1", speaker_label)
