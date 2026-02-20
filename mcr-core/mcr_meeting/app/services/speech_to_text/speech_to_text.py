"""Speech to text service with speaker diarization using pyannote and faster-whisper"""

from io import BytesIO
from typing import List

from loguru import logger

from mcr_meeting.app.exceptions.exceptions import InvalidAudioFileError
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
    TranscriptionSegment,
)
from mcr_meeting.app.services.audio_pre_transcription_processing_service import (
    filter_noise_from_audio_bytes,
    normalize_audio_bytes_to_wav_bytes,
)
from mcr_meeting.app.services.feature_flag_service import (
    get_feature_flag_client,
)
from mcr_meeting.app.services.speech_to_text.diarization_processor import (
    DiarizationProcessor,
)
from mcr_meeting.app.services.speech_to_text.transcription_post_process import (
    merge_consecutive_segments_per_speaker,
)
from mcr_meeting.app.services.speech_to_text.transcription_processor import (
    TranscriptionProcessor,
)
from mcr_meeting.app.services.speech_to_text.types import DiarizationSegment
from mcr_meeting.app.services.speech_to_text.utils import (
    diarize_vad_transcription_segments,
    get_vad_segments_from_diarization,
)


class SpeechToTextPipeline:
    """Pipeline to convert speech in audio bytes to text with speaker diarization"""

    def __init__(self) -> None:
        self.transcription_processor = TranscriptionProcessor()
        self.diarization_processor = DiarizationProcessor()

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
        return self.transcription_processor.transcribe(
            audio_bytes=audio_bytes, vad_spans=vad_spans
        )

    def diarize_audio(
        self,
        audio_bytes: BytesIO,
    ) -> List[DiarizationSegment]:
        """Perform speaker diarization on audio bytes

        Args:
            audio_bytes (BytesIO): The input audio bytes.

        Returns:
            List[DiarizationSegment]: The diarization result with speaker segments.
        """
        return self.diarization_processor.diarize(audio_bytes=audio_bytes)

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
