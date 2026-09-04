export const FFT_SIZE = 256; // Number of audio samples analyzed at each instant. A higher value gives a more precise analysis but consumes more resources. 256 is a good compromise between precision and performance.
export const SMOOTHING_TIME_CONSTANT = 0.8; // Smoothing time constant for the audio analysis. A higher value gives a more important smoothing but may introduce a delay in the response. 0.8 is a good compromise between precision and reactivity.
export const DECAY_RATE = 0.02; // Decay rate for the audio analysis. A higher value gives a faster decay but may introduce abrupt variations. 0.02 is a good compromise between precision and reactivity.
export const GAIN = 1.0; // Gain factor for the audio analysis. A higher value gives a more important gain but may introduce noise. 1.0 is a good compromise between precision and reactivity.
export const AUDIO_SAMPLE_MIDPOINT = 128; // 8-bit audio samples range from 0-255, so 128 is the midpoint

export const MIN_DURATION_FOR_RATE_CHECK_MS = 30_000; // Below this recording duration we don't trust the effective sample rate (too few samples to judge).
export const MIN_EFFECTIVE_SAMPLE_RATE = 5; // Foreground rAF runs at ~60 samples/s; a throttled background tab drops far below this.
export const BACKGROUND_RATIO_THRESHOLD = 0.5; // If the tab spent more than this fraction of the session backgrounded, the rAF sampler was throttled.

export const LOOPBACK_DEVICE_REGEX = /^Monitor of /i; // PulseAudio loopback source ("Monitor of <sink>") — captures system output, never a voice.
export const CONTINUITY_DEVICE_REGEX = /iPhone|iPad|Continuity/i; // macOS Continuity devices that the system "default" mic may silently resolve to.
export const BUILTIN_DEVICE_REGEX = /built-?in/i; // A real built-in microphone, used as the "a working alternative existed" signal.

export const LIVE_NO_SIGNAL_LEVEL_THRESHOLD = 0.01; // Compared against the level the recording monitor produces (gain 2.5, set in use-recording-monitor.ts), not against GAIN above: digital zero passes under it, a working microphone's noise floor does not.
export const LIVE_NO_SIGNAL_DURATION_MS = 10_000; // Continuous time under the threshold before alerting; absorbs micro-dropouts.
export const LIVE_NO_SIGNAL_GRACE_MS = 3_000; // A microphone just switched to takes a moment to deliver its first samples.
export const LIVE_NO_SIGNAL_REPEAT_MS = 10_000; // Spacing between beeps while the alert holds.
export const LIVE_NO_SIGNAL_MAX_BEEPS = 5; // We warn, we don't harass: the visual alert stays, the sound stops.
