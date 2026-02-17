"""Utility functions for dataset standardisation."""

from pathlib import Path

from mcr_meeting.evaluation.eval_types import TranscriptionOutput


def save_transcription_output(
    transcription: TranscriptionOutput,
    output_path: Path,
) -> None:
    """
    Save a TranscriptionOutput object to a JSON file.

    Uses Pydantic's model_dump_json() method to serialize the object with
    proper formatting. Creates parent directories if they don't exist.

    Args:
        transcription: TranscriptionOutput Pydantic model to save
        output_path: Path where the JSON file will be saved

    Example:
        >>> from pathlib import Path
        >>> output = parse_trs_file(Path("data/ref_noisy/bres_m1_08.trs"))
        >>> save_transcription_output(
        ...     output,
        ...     Path("data/reference_transcripts/bres_m1_08.json")
        ... )
    """
    # Create parent directories if they don't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Use Pydantic's model_dump_json for serialization with indentation
    json_content = transcription.model_dump_json(indent=2)

    # Write to file
    output_path.write_text(json_content, encoding="utf-8")
