"""Speech to text service with speaker diarization using pyannote and faster-whisper"""

from io import BytesIO

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
from mcr_meeting.app.services.correct_spelling_mistakes.spelling_corrector import (
    SpellingCorrector,
)
from mcr_meeting.app.services.feature_flag_service import (
    get_feature_flag_client,
)
from mcr_meeting.app.services.speech_to_text.diarization_processor import (
    DiarizationProcessor,
)
from mcr_meeting.app.services.speech_to_text.transcription_post_process import (
    merge_consecutive_segments_per_speaker,
    remove_hallucinations,
)
from mcr_meeting.app.services.speech_to_text.transcription_processor import (
    TranscriptionProcessor,
)
from mcr_meeting.app.services.speech_to_text.types import DiarizationSegment
from mcr_meeting.app.services.speech_to_text.utils import (
    compute_transcription_chunks,
    diarize_vad_transcription_segments,
)
from mcr_meeting.app.services.speech_to_text.utils.types import TimeSpan


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
        diarized_transcription_segments: list[DiarizedTranscriptionSegment],
    ) -> list[DiarizedTranscriptionSegment]:
        """Post-process diarized transcription segments.

        This includes merging consecutive segments from the same speaker.

        Args:
            diarized_transcription_segments (List[DiarizedTranscriptionSegment]): The diarized transcription segments.

        Returns:
            List[DiarizedTranscriptionSegment]: The post-processed diarized transcription segments.
        """
        feature_flag_client = get_feature_flag_client()

        if not diarized_transcription_segments:
            logger.warning("No transcription segments found")
            raise InvalidAudioFileError("No transcription segments found")
        merged_segments = merge_consecutive_segments_per_speaker(
            diarized_transcription_segments
        )
        cleaned_segments = remove_hallucinations(merged_segments)

        if feature_flag_client.is_enabled("spelling_correction"):
            logger.debug("Spelling correction enabled, correcting segments")
            corrector = SpellingCorrector()
            cleaned_segments = corrector.correct(cleaned_segments)
        else:
            logger.debug("Spelling correction disabled, skipping correction")
        return cleaned_segments

    def transcribe_audio(
        self,
        audio_bytes: BytesIO,
        chunk_spans: list[TimeSpan],
    ) -> list[TranscriptionSegment]:
        """Transcribe full audio bytes to text.

        Args:
            audio_bytes (BytesIO): The input audio bytes.
            chunk_spans (List[TimeSpan]): The time spans to split the audio into for transcription.

        Returns:
            List[TranscriptionSegment]: A list of TranscriptionSegment objects containing the transcription results with speaker labels.
        """
        return self.transcription_processor.transcribe(
            audio_bytes=audio_bytes, chunk_spans=chunk_spans
        )

    def diarize_audio(
        self,
        audio_bytes: BytesIO,
    ) -> list[DiarizationSegment]:
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
    ) -> list[DiarizedTranscriptionSegment]:
        """Transcribe full audio bytes to text with speaker diarization"""

        logger.debug("🏁 Starting speech-to-text pipeline with pre-processing.")

        pre_processed_audio_bytes = self.pre_process(audio_bytes)

        diarization_result = self.diarize_audio(
            pre_processed_audio_bytes,
        )

        if not diarization_result:
            logger.warning("No diarization result. Returning empty transcription.")
            return []

        transcription_chunk_spans: list[TimeSpan] = compute_transcription_chunks(
            diarization_result
        )

        transcription_segments = self.transcribe_audio(
            pre_processed_audio_bytes, transcription_chunk_spans
        )

        diarized_transcription_segments = diarize_vad_transcription_segments(
            transcription_segments, diarization_result
        )

        cleaned_segments = self.post_process(diarized_transcription_segments)

        first_words = (
            " ".join(cleaned_segments[0].text.split()[:10]) if cleaned_segments else ""
        )
        logger.debug(
            "✅ Speech-to-text pipeline completed for transcription starting with: [{}...]",
            first_words,
        )

        return cleaned_segments
