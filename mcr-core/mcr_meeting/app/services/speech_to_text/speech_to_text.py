"""Speech to text service with speaker diarization using pyannote and faster-whisper"""

import tempfile
from io import BytesIO
from typing import List

import numpy as np
from faster_whisper import WhisperModel
from loguru import logger
from numpy.typing import NDArray

from mcr_meeting.app.configs.base import (
    WhisperTranscriptionSettings,
)
from mcr_meeting.app.exceptions.exceptions import InvalidAudioFileError
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
    TranscriptionSegment,
)
from mcr_meeting.app.services.audio_pre_transcription_processing_service import (
    filter_noise_from_audio_bytes,
    normalize_audio_bytes_to_wav_bytes,
)
from mcr_meeting.app.services.feature_flag_service import get_feature_flag_client
from mcr_meeting.app.services.speech_to_text.transcription_post_process import (
    merge_consecutive_segments_per_speaker,
)
from mcr_meeting.app.services.speech_to_text.types import DiarizationSegment
from mcr_meeting.app.services.speech_to_text.utils import (
    convert_to_french_speaker,
    diarize_vad_transcription_segments,
    get_vad_segments_from_diarization,
    split_audio_on_timestamps,
)
from mcr_meeting.app.services.speech_to_text.utils.models import (
    get_diarization_pipeline,
    get_transcription_model,
)

transcription_settings = WhisperTranscriptionSettings()


class SpeechToTextPipeline:
    """Pipeline to convert speech in audio bytes to text with speaker diarization"""

    def __init__(self) -> None:
        pass

    def pre_process(self, audio_bytes: BytesIO) -> BytesIO:
        """Pre-process audio bytes before transcription and diarization.

        This includes normalizing the audio to WAV format and applying noise filtering if enabled.

        Args:
            audio_bytes (BytesIO): The input audio bytes.

        Returns:
            BytesIO: The pre-processed audio bytes.
        """
        feature_flag_client = get_feature_flag_client()
        normalized_audio_bytes = normalize_audio_bytes_to_wav_bytes(audio_bytes)
        # Apply noise filtering only if feature flag is enabled
        if feature_flag_client.is_enabled("audio_noise_filtering"):
            logger.debug("Noise filtering enabled")
            pre_processed_bytes = filter_noise_from_audio_bytes(normalized_audio_bytes)
        else:
            logger.debug("Noise filtering disabled, skipping filtering step")
            pre_processed_bytes = normalized_audio_bytes

        return pre_processed_bytes

    def post_process(
        self,
        diarized_transcription_segments: List[DiarizedTranscriptionSegment],
    ) -> List[DiarizedTranscriptionSegment]:
        """Post-process diarized transcription segments.

        This includes merging consecutive segments from the same speaker.

        Args:
            diarized_transcription_segments (List[DiarizedTranscriptionSegment]): The diarized transcription segments.

        Returns:
            List[DiarizedTranscriptionSegment]: The post-processed diarized transcription segments.
        """
        if not diarized_transcription_segments:
            logger.warning("No transcription segments found")
            raise InvalidAudioFileError("No transcription segments found")
        merged_segments = merge_consecutive_segments_per_speaker(
            diarized_transcription_segments
        )
        return merged_segments

    def transcribe_audio_chunk(
        self,
        audio: NDArray[np.float32],
        transcription_model: WhisperModel,
    ) -> List[TranscriptionSegment]:
        """Transcribe audio array:q to text with speaker diarization

        Args:
            audio (NDArray): The input audio array.
            transcription_model (WhisperModel): The transcription model.

        Returns:
            List[TranscriptionSegment]: A list of TranscriptionSegment objects containing the transcription results with speaker labels.
        """
        logger.debug("Audio loaded shape: {}, dtype: {}", audio.shape, audio.dtype)

        segments, info = transcription_model.transcribe(
            audio,
            language=transcription_settings.language,
            word_timestamps=transcription_settings.word_timestamps,
            initial_prompt="Ceci est la transcription d'une réunion d'équipe avec plusieurs intervenants ; reformule le texte dans un langage naturel et fluide, sans répétitions.",
        )

        result = list(segments)

        logger.debug("Transcription info: {}", info)

        if not result:
            logger.debug("No segments found in transcription result.")
            return []

        transcription_segments = [
            TranscriptionSegment(
                id=seg.id,
                start=seg.start,
                end=seg.end,
                text=seg.text,
            )
            for seg in result
        ]

        return transcription_segments

    def transcribe_audio(
        self,
        audio_bytes: BytesIO,
        vad_spans: List[DiarizationSegment],
    ) -> List[TranscriptionSegment]:
        """Transcribe full audio bytes to text.

        Args:
            audio_bytes (BytesIO): The input audio bytes.
            vad_spans (List[DiarizationSegment]): The VAD segments to split the audio into for transcription.

        Returns:
            List[TranscriptionSegment]: A list of TranscriptionSegment objects containing the transcription results with speaker labels.
        """
        transcription_inputs = split_audio_on_timestamps(audio_bytes, vad_spans)

        logger.debug("Number of transcription inputs: {}", len(transcription_inputs))

        transciription_model = get_transcription_model()
        transcription_segments: List[TranscriptionSegment] = []

        for idx, chunk in enumerate(transcription_inputs):
            logger.debug(
                "Transcribing vad chunk: start={}, end={}",
                chunk.diarization.start,
                chunk.diarization.end,
            )
            chunk_transcription_segments = self.transcribe_audio_chunk(
                chunk.audio, transciription_model
            )
            if not chunk_transcription_segments:
                logger.debug(
                    "No transcription for this chunk: start: {} - end: {}.",
                    chunk.diarization.start,
                    chunk.diarization.end,
                )
                continue
            logger.debug(
                "Number of transcription segments in one chunk: {}",
                len(chunk_transcription_segments),
            )

            for segment in chunk_transcription_segments:
                transcription_segments.append(
                    TranscriptionSegment(
                        id=idx,
                        start=segment.start + chunk.diarization.start,
                        end=segment.end + chunk.diarization.start,
                        text=segment.text,
                    )
                )

        return transcription_segments

    def diarize_audio(
        self,
        audio_bytes: BytesIO,
    ) -> List[DiarizationSegment]:
        """Perform speaker diarization on audio bytes

        Args:
            audio_bytes (BytesIO): The input audio bytes.

        Returns:
            Any: The diarization result from the pyannote pipeline.
        """
        diarization_pipeline = get_diarization_pipeline()

        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp_audio:
            tmp_audio.write(audio_bytes.getvalue())
            tmp_audio_path = tmp_audio.name

            pyannote_diarization = diarization_pipeline(tmp_audio_path)

            diarization_segments = [
                DiarizationSegment(
                    start=segment.start,
                    end=segment.end,
                    speaker=convert_to_french_speaker(speaker),
                )
                for segment, _, speaker in pyannote_diarization.itertracks(
                    yield_label=True
                )
            ]

            return diarization_segments

    def run(
        self,
        audio_bytes: BytesIO,
    ) -> List[DiarizedTranscriptionSegment]:
        """Transcribe full audio bytes to text with speaker diarization"""

        logger.debug("Starting speech-to-text pipeline with pre-processing.")

        pre_processed_audio_bytes = self.pre_process(audio_bytes)

        diarization_result = self.diarize_audio(
            pre_processed_audio_bytes,
        )

        if not diarization_result:
            logger.debug("No diarization result. Returning empty transcription.")
            return []

        vad_spans: List[DiarizationSegment] = get_vad_segments_from_diarization(
            diarization_result
        )

        transcription_segments = self.transcribe_audio(
            pre_processed_audio_bytes, vad_spans
        )

        diarized_transcription_segments = diarize_vad_transcription_segments(
            transcription_segments, diarization_result
        )

        merged_segments = self.post_process(diarized_transcription_segments)

        logger.debug("Final transcription segments: {}", merged_segments)

        return merged_segments
