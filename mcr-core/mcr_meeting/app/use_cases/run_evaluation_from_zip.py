import tempfile
import zipfile
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

from loguru import logger

from mcr_meeting.app.domain.evaluation_zip import (
    RAW_AUDIOS_DIR,
    REFERENCE_TRANSCRIPTS_DIR,
    find_evaluation_dataset_root,
)
from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment
from mcr_meeting.evaluation.asr.evaluation_pipeline import ASREvaluationPipeline
from mcr_meeting.evaluation.cli.utils import load_evaluation_inputs


def run_evaluation_from_zip(
    zip_data: bytes,
    transcribe_audio: Callable[[BytesIO], list[DiarizedTranscriptionSegment]],
) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        with zipfile.ZipFile(BytesIO(zip_data)) as z:
            z.extractall(temp_path)

        logger.info("Extracted zip file to temporary directory: {}", temp_path)

        base_path = find_evaluation_dataset_root(temp_path, list(temp_path.rglob("*")))
        if base_path is None:
            raise ValueError(
                f"Zip file must contain '{RAW_AUDIOS_DIR}' and "
                f"'{REFERENCE_TRANSCRIPTS_DIR}' folders (at any root level)."
            )

        evaluation_inputs = load_evaluation_inputs(
            audio_dir=base_path / RAW_AUDIOS_DIR,
            ref_dir=base_path / REFERENCE_TRANSCRIPTS_DIR,
        )
        if not evaluation_inputs:
            raise ValueError("No valid evaluation inputs found in the zip file.")

        pipeline = ASREvaluationPipeline(
            inputs=evaluation_inputs, transcribe_audio=transcribe_audio
        )
        output_dir = temp_path / "outputs"
        output_dir.mkdir()

        pipeline.run_evaluation(output_dir=output_dir)
