export const FFT_SIZE = 256; // Number of audio samples analyzed at each instant. A higher value gives a more precise analysis but consumes more resources. 256 is a good compromise between precision and performance.
export const SMOOTHING_TIME_CONSTANT = 0.8; // Smoothing time constant for the audio analysis. A higher value gives a more important smoothing but may introduce a delay in the response. 0.8 is a good compromise between precision and reactivity.
export const DECAY_RATE = 0.02; // Decay rate for the audio analysis. A higher value gives a faster decay but may introduce abrupt variations. 0.02 is a good compromise between precision and reactivity.
export const GAIN = 1.0; // Gain factor for the audio analysis. A higher value gives a more important gain but may introduce noise. 1.0 is a good compromise between precision and reactivity.
export const AUDIO_SAMPLE_MIDPOINT = 128; // 8-bit audio samples range from 0-255, so 128 is the midpoint


export const MIN_DURATION_FOR_RATE_CHECK_MS = 30_000; // Below this recording duration we don't trust the effective sample rate (too few samples to judge).
export const MIN_EFFECTIVE_SAMPLE_RATE = 5; // Foreground rAF runs at ~60 samples/s; a throttled background tab drops far below this.
export const BACKGROUND_RATIO_THRESHOLD = 0.5; // If the tab spent more than this fraction of the session backgrounded, the rAF sampler was throttled.
