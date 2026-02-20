"""Script that standardises the noisy datasets in order its ground truth can be used by our evaluation pipeline."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment
from mcr_meeting.evaluation.eval_types import TranscriptionOutput

from scripts.dataset_standardisation.utils import save_transcription_output


def _extract_text_content(element: ET.Element) -> str:
    """
    Extract text content from an XML element, excluding Event and Comment tags.

    Uses Pydantic-like approach by building a validated string from element parts.

    Args:
        element: XML element to extract text from

    Returns:
        Extracted text with HTML entities decoded
    """
    text_parts = []

    # Get text directly in this element
    if element.text:
        text_parts.append(element.text)

    # Iterate through child elements
    for child in element:
        # Skip Event and Comment tags - they're annotations, not transcription
        if child.tag in ("Event", "Comment"):
            # But include tail text after the tag
            if child.tail:
                text_parts.append(child.tail)
        elif child.tag == "Sync":
            # Sync tags mark time boundaries - don't include their tail here
            continue
        else:
            # Include text from other elements
            text_parts.append(_extract_text_content(child))
            if child.tail:
                text_parts.append(child.tail)

    return "".join(text_parts)


def _clean_text(text: str) -> str:
    """
    Clean text by normalizing whitespace while preserving special markers.

    Keeps overlap markers (<, >) and special symbols (***) as per requirements.
    Uses simple string processing (Pydantic models work with clean strings).

    Args:
        text: Raw text to clean

    Returns:
        Cleaned text with normalized whitespace
    """
    # Collapse multiple spaces into one
    text = re.sub(r"\s+", " ", text)
    # Strip leading/trailing whitespace
    text = text.strip()
    return text


def _extract_text_between_syncs(
    turn: ET.Element, start_sync: ET.Element | None, end_sync: ET.Element | None
) -> str:
    """
    Extract text content between two Sync points in a Turn.

    Args:
        turn: The Turn element containing the text
        start_sync: Starting Sync element (None for turn start)
        end_sync: Ending Sync element (None for turn end)

    Returns:
        Extracted and cleaned text between the sync points
    """
    # Get all children of the turn
    children = list(turn)

    # Find indices of sync points
    start_idx = 0 if start_sync is None else children.index(start_sync) + 1
    end_idx = len(children) if end_sync is None else children.index(end_sync)

    # Extract text from elements between syncs
    text_parts = []

    # Handle text after start_sync (or turn start)
    if start_sync is not None and start_sync.tail:
        text_parts.append(start_sync.tail)
    elif start_sync is None and turn.text:
        text_parts.append(turn.text)

    # Process elements between syncs
    for child in children[start_idx:end_idx]:
        if child.tag in ("Event", "Comment"):
            # Skip events/comments but keep tail text
            if child.tail:
                text_parts.append(child.tail)
        elif child.tag == "Sync":
            # Should not happen in our slice, but handle it
            continue
        else:
            # Extract content from other elements
            text_parts.append(_extract_text_content(child))
            if child.tail:
                text_parts.append(child.tail)

    return "".join(text_parts)


def parse_trs_file(trs_path: Path) -> TranscriptionOutput:
    """
    Parse a .trs XML file and return a TranscriptionOutput Pydantic model.

    This function converts TRS (Transcriber) format files from the noisy dataset
    into TranscriptionOutput objects that can be serialized to JSON for the
    evaluation pipeline.

    The TRS format contains:
    - Speakers with IDs and names
    - Turns with speaker attribution and time boundaries
    - Sync points marking timestamps within turns
    - Text content with annotations (Events, Comments)

    Args:
        trs_path: Path to the .trs file to parse

    Returns:
        TranscriptionOutput: Pydantic model containing diarized segments
        with sequential IDs, timestamps, text, and speaker labels

    Raises:
        FileNotFoundError: If trs_path does not exist
        ET.ParseError: If XML parsing fails

    Example:
        >>> from pathlib import Path
        >>> trs_file = Path("data/noisy_dataset/ref_noisy/bres_m1_08.trs")
        >>> output = parse_trs_file(trs_file)
        >>> json_str = output.model_dump_json(indent=2)
    """
    # Parse XML with ISO-8859-1 encoding (French characters)
    tree = ET.parse(str(trs_path), ET.XMLParser(encoding="ISO-8859-1"))
    root = tree.getroot()

    segments: list[DiarizedTranscriptionSegment] = []
    segment_id = 0

    # Find all Turn elements in the document
    for turn in root.findall(".//Turn"):
        speaker = turn.get("speaker", "unknown")
        turn_start = float(turn.get("startTime", 0))
        turn_end = float(turn.get("endTime", 0))

        # Find all Sync points within this turn
        syncs = turn.findall("Sync")

        if not syncs:
            # No sync points - treat entire turn as one segment
            text = _extract_text_content(turn)
            text = _clean_text(text)

            if text:  # Skip empty segments
                # Use Pydantic model constructor with validation
                segment = DiarizedTranscriptionSegment(
                    id=segment_id,
                    start=turn_start,
                    end=turn_end,
                    text=text,
                    speaker=speaker,
                )
                segments.append(segment)
                segment_id += 1
        else:
            # Process segments between sync points
            for i, sync in enumerate(syncs):
                start_time = float(sync.get("time", 0))

                # Determine end time (next sync or turn end)
                if i + 1 < len(syncs):
                    end_time = float(syncs[i + 1].get("time", 0))
                    next_sync = syncs[i + 1]
                else:
                    end_time = turn_end
                    next_sync = None

                # Extract text between this sync and the next
                text = _extract_text_between_syncs(turn, sync, next_sync)
                text = _clean_text(text)

                if text:  # Skip empty segments
                    # Use Pydantic model constructor - validates types automatically
                    segment = DiarizedTranscriptionSegment(
                        id=segment_id,
                        start=start_time,
                        end=end_time,
                        text=text,
                        speaker=speaker,
                    )
                    segments.append(segment)
                    segment_id += 1

    # Return TranscriptionOutput - Pydantic validates the structure
    return TranscriptionOutput(segments=segments)


def main() -> None:
    """
    Convert all .trs files from the noisy dataset to JSON format.

    Processes all .trs files in the ref_noisy directory and saves them
    as JSON files in the reference_transcripts directory, maintaining
    the same filenames (with .json extension).

    This enables the noisy dataset to be used in the evaluation pipeline
    which expects TranscriptionOutput JSON files.
    """
    # Define input and output directories
    ref_noisy_dir = Path("mcr_meeting/evaluation/data/noisy_dataset/ref_noisy")
    output_dir = Path("mcr_meeting/evaluation/data/noisy_dataset/reference_transcripts")

    # Get all .trs files
    trs_files = list(ref_noisy_dir.glob("*.trs"))

    if not trs_files:
        print(f"⚠️  No .trs files found in {ref_noisy_dir}")
        return

    print(f"Found {len(trs_files)} .trs files to convert")
    print(f"Output directory: {output_dir}\n")

    # Process each file
    converted_count = 0
    failed_count = 0

    for trs_file in trs_files:
        try:
            # Parse the .trs file
            transcription = parse_trs_file(trs_file)

            # Create output path with same filename but .json extension
            output_path = output_dir / f"{trs_file.stem}.json"

            # Save to JSON
            save_transcription_output(transcription, output_path)

            print(
                f"✓ {trs_file.name} → {output_path.name} ({len(transcription.segments)} segments)"
            )
            converted_count += 1

        except Exception as e:
            print(f"✗ {trs_file.name} - Error: {e}")
            failed_count += 1

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Conversion complete:")
    print(f"  ✓ Successfully converted: {converted_count}")
    if failed_count > 0:
        print(f"  ✗ Failed: {failed_count}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
