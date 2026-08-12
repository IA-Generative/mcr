from io import BytesIO

from loguru import logger

from mcr_meeting.app.domain.audio import (
    audio_bytes_to_wav_bytes,
    check_audio_is_not_silent,
    filter_noise_from_audio_bytes,
    is_audio_noisy,
)
from mcr_meeting.app.infrastructure.sentry import span
from mcr_meeting.app.infrastructure.unleash import (
    FeatureFlag,
    get_feature_flag_client,
)


def preprocess_audio(audio_bytes: BytesIO) -> BytesIO:
    # ffmpeg runs as a subprocess and is invisible to auto-instrumentation, so
    # each step is spanned here — at the seam that owns the calls — to keep the
    # trace's ffmpeg time named rather than the domain layer aware of Sentry.
    feature_flag_client = get_feature_flag_client()
    phase_aware_downmix = feature_flag_client.is_enabled(
        FeatureFlag.AUDIO_PHASE_AWARE_DOWNMIX
    )
    with span("ffmpeg.transcode", "audio_bytes_to_wav_bytes"):
        wav_audio_bytes = audio_bytes_to_wav_bytes(audio_bytes, phase_aware_downmix)

    with span("ffmpeg.silencedetect", "check_audio_is_not_silent"):
        check_audio_is_not_silent(wav_audio_bytes)

    if not feature_flag_client.is_enabled(FeatureFlag.AUDIO_NOISE_FILTERING):
        logger.debug("Noise filtering disabled, skipping filtering step")
        return wav_audio_bytes

    with span("ffmpeg.analyze", "is_audio_noisy"):
        audio_is_noisy = is_audio_noisy(wav_audio_bytes)

    if audio_is_noisy:
        logger.debug("Noisy audio detected, applying noise filtering")
        with span("ffmpeg.denoise", "filter_noise_from_audio_bytes"):
            return filter_noise_from_audio_bytes(wav_audio_bytes)

    logger.debug("Clean audio detected, not applying noise filtering")
    return wav_audio_bytes
