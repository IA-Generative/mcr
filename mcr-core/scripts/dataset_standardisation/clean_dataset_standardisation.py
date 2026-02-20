"""Script that standardises the clean datasets in order its ground truth can be used by our evaluation pipeline."""

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from loguru import logger

from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment
from mcr_meeting.app.services.speech_to_text.transcription_post_process import (
    merge_consecutive_segments_per_speaker,
)
from mcr_meeting.evaluation.eval_types import TranscriptionOutput
from scripts.dataset_standardisation.utils import save_transcription_output


def load_individual_ground_truth_files(
    ground_truth_dir: Path,
) -> Dict[str, List[dict]]:
    """
    Load and group individual speaker JSON files by meeting_id.

    Args:
        ground_truth_dir (Path): Directory containing individual ground truth JSON files.

    Returns:
        Dict[str, List[dict]]: Dictionary mapping meeting_id to list of speaker data.
            Each speaker data contains: speaker_id, audio_id, segments, file_path.

    Example:
        >>> files = load_individual_ground_truth_files(Path("individual_ground_truth/"))
        >>> # {"004c_PAPH": [{"speaker_id": "013", "segments": [...], ...}, ...]}
    """
    grouped_files: Dict[str, List[dict]] = defaultdict(list)

    logger.info("Scanning directory: {}", ground_truth_dir)

    if not ground_truth_dir.exists():
        logger.warning("Directory does not exist: {}", ground_truth_dir)
        return grouped_files

    for json_file in ground_truth_dir.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            meeting_id = data.get("meeting_id")
            if not meeting_id:
                logger.warning("Missing meeting_id in file: {}, skipping", json_file)
                continue

            grouped_files[meeting_id].append(
                {
                    "speaker_id": data.get("speaker_id", "unknown"),
                    "audio_id": data.get("audio_id", "unknown"),
                    "segments": data.get("segments", []),
                    "file_path": json_file,
                }
            )
            logger.debug(
                "Loaded {} with {} segments",
                json_file.name,
                len(data.get("segments", [])),
            )

        except Exception as e:
            logger.error("Error loading file {}: {}", json_file, e)
            continue

    logger.info(
        "Found {} meetings with {} total files",
        len(grouped_files),
        sum(len(v) for v in grouped_files.values()),
    )
    return dict(grouped_files)


def convert_segment_to_word_level_segments(
    segment: dict, speaker_id: str
) -> List[dict]:
    """
    Convert individual ground truth segment to word-level DiarizedTranscriptionSegment format.

    Creates one segment per word from the 'words' array in the segment.

    Args:
        segment (dict): Segment from individual ground truth file with keys:
            'words' (list of word objects with 'word', 'start', 'end').
        speaker_id (str): Speaker identifier (e.g., "013").

    Returns:
        List[dict]: List of segment dicts (one per word) ready for DiarizedTranscriptionSegment creation.
            Note: 'id' field is not assigned here - will be done after sorting.

    Example:
        >>> segment = {"words": [{"word": "hello", "start": 1.0, "end": 1.5}, ...]}
        >>> convert_segment_to_word_level_segments(segment, "013")
        [{"text": "hello", "start": 1.0, "end": 1.5, "speaker": "spk013"}, ...]
    """
    words = segment.get("words", [])
    word_segments = []

    for word_obj in words:
        word_segments.append(
            {
                "text": word_obj["word"],
                "start": word_obj["start"],
                "end": word_obj["end"],
                "speaker": f"spk{speaker_id}",
            }
        )

    return word_segments


def merge_speakers_for_meeting(speaker_files: List[dict]) -> TranscriptionOutput:
    """
    Merge all speakers' segments for one meeting at word-level, then merge consecutive segments per speaker.

    This function:
    1. Converts each segment to word-level segments (one segment per word)
    2. Collects all word segments from all speakers
    3. Sorts chronologically by start time
    4. Assigns sequential IDs
    5. Merges consecutive segments from the same speaker to reduce total segments

    Args:
        speaker_files (List[dict]): List of speaker data dicts, each containing:
            'speaker_id', 'segments', 'audio_id', 'file_path'.

    Returns:
        TranscriptionOutput: Pydantic model containing merged segments.

    Example:
        >>> speaker_files = [
        ...     {"speaker_id": "013", "segments": [{"words": [{"word": "hello", ...}]}]},
        ...     {"speaker_id": "014", "segments": [{"words": [{"word": "world", ...}]}]}
        ... ]
        >>> output = merge_speakers_for_meeting(speaker_files)
        >>> # TranscriptionOutput with word-level segments merged by consecutive speaker
    """
    all_word_segments = []

    # Collect all word-level segments from all speakers
    for speaker_data in speaker_files:
        speaker_id = speaker_data["speaker_id"]
        for segment in speaker_data["segments"]:
            # Convert to word-level segments (returns list)
            word_segments = convert_segment_to_word_level_segments(segment, speaker_id)
            all_word_segments.extend(word_segments)

    logger.debug(
        "Collected {} word-level segments from {} speakers",
        len(all_word_segments),
        len(speaker_files),
    )

    # Sort by start time (chronological order)
    all_word_segments.sort(key=lambda x: x["start"])

    # Assign sequential IDs and create DiarizedTranscriptionSegment objects
    diarized_segments = [
        DiarizedTranscriptionSegment(id=i, **segment)
        for i, segment in enumerate(all_word_segments)
    ]

    # Merge consecutive segments from the same speaker
    merged_segments = merge_consecutive_segments_per_speaker(diarized_segments)

    logger.debug(
        "After merging consecutive speakers: {} segments (reduced from {})",
        len(merged_segments),
        len(diarized_segments),
    )

    return TranscriptionOutput(segments=merged_segments)


def process_and_save_meeting(
    meeting_id: str, speaker_files: List[dict], output_dir: Path
) -> bool:
    """
    Process one meeting by merging speakers and save to reference_transcripts format.

    Args:
        meeting_id (str): Meeting identifier (e.g., "004c_PAPH").
        speaker_files (List[dict]): List of speaker data for this meeting.
        output_dir (Path): Directory where merged JSON will be saved.

    Returns:
        bool: True if processing succeeded, False otherwise.
    """
    logger.info(
        "Processing meeting '{}' with {} speakers", meeting_id, len(speaker_files)
    )

    try:
        # Merge all speakers
        transcription_output = merge_speakers_for_meeting(speaker_files)

        # Save to JSON using utility function
        output_file = output_dir / f"{meeting_id}.json"
        save_transcription_output(transcription_output, output_file)

        logger.info(
            "Saved {} segments to: {}", len(transcription_output.segments), output_file
        )
        return True

    except Exception as e:
        logger.error("Failed to process meeting '{}': {}", meeting_id, e)
        return False


def main() -> None:
    """
    Group individual ground truth files by meeting and merge speakers.

    Reads JSON files from individual_ground_truth, groups them by meeting_id
    (first 4 characters of filename), merges speakers chronologically,
    and saves results to reference_transcripts.
    """
    # Define paths
    individual_ground_truth_path = Path(
        "mcr_meeting/evaluation/data/clean_dataset/individual_ground_truth"
    )
    raw_ground_truth_path = Path(
        "mcr_meeting/evaluation/data/clean_dataset/reference_transcripts"
    )

    logger.info("Starting ground truth transcription merging process")
    logger.info("Input directory: {}", individual_ground_truth_path)
    logger.info("Output directory: {}", raw_ground_truth_path)

    # Load and group by meeting
    meetings = load_individual_ground_truth_files(individual_ground_truth_path)

    if not meetings:
        logger.warning("No meetings found. Exiting.")
        return

    # Process each meeting
    success_count = 0
    failure_count = 0

    for meeting_id, speaker_files in meetings.items():
        if process_and_save_meeting(meeting_id, speaker_files, raw_ground_truth_path):
            success_count += 1
        else:
            failure_count += 1

    logger.info(
        "Ground truth merging completed: {} meetings succeeded, {} meetings failed",
        success_count,
        failure_count,
    )


if __name__ == "__main__":
    main()
