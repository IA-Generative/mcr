import { ref } from 'vue';
import { AudioLevelMonitor } from '@/utils/audio-level-monitor';
import type { AudioDeviceInfo } from '@/composables/use-recorder';
import {
  MIN_DURATION_FOR_RATE_CHECK_MS,
  MIN_EFFECTIVE_SAMPLE_RATE,
  BACKGROUND_RATIO_THRESHOLD,
} from '@/config/audioMonitor';
import * as Sentry from '@sentry/vue';

export const SILENCE_LEVEL_THRESHOLD = 0.05;
export const SILENCE_RATIO_THRESHOLD = 0.98;

export type SilenceCause = 'sampler-throttled' | 'true-silence';

export const SILENCE_MESSAGES: Record<SilenceCause, string> = {
  'sampler-throttled': 'Silent recording: sampler throttled (background tab)',
  'true-silence': 'Silent recording: true silence (no mic signal)',
};

export type RecordingSessionStats = {
  maxAudioLevel: number;
  meanAudioLevel: number;
  silenceRatio: number;
  sampleCount: number;
  emptyChunkCount: number;
  trackMuteEvents: number;
  recorderErrorEvents: number;
  deviceLabel: string;
  deviceSettings: MediaTrackSettings | null;
  requestedDeviceId: string | null;
  availableDevices: AudioDeviceInfo[];
  // Sampling rate instrumentation (detects a rAF sampler throttled in a background tab).
  durationMs: number;
  effectiveSampleRate: number;
  backgroundedMs: number;
  visibilityHiddenCount: number;
};

export type RecordingMonitorOptions = {
  onEmptyChunk?: (chunkIndex: number) => void;
  onRecorderError?: (event: Event) => void;
};

export type RecordingMonitorContext = {
  stream: MediaStream;
  recorder: MediaRecorder;
  meetingId: number;
  requestedDeviceId: string | null;
  availableDevices: AudioDeviceInfo[];
};

function createEmptyStats(): RecordingSessionStats {
  return {
    maxAudioLevel: 0,
    meanAudioLevel: 0,
    silenceRatio: 1,
    sampleCount: 0,
    emptyChunkCount: 0,
    trackMuteEvents: 0,
    recorderErrorEvents: 0,
    deviceLabel: '',
    deviceSettings: null,
    requestedDeviceId: null,
    availableDevices: [],
    durationMs: 0,
    effectiveSampleRate: 0,
    backgroundedMs: 0,
    visibilityHiddenCount: 0,
  };
}

export function classifySilence(stats: RecordingSessionStats): SilenceCause {
  if (isSamplerThrottled(stats)) return 'sampler-throttled'; // sampler throttled in a background tab:
  return 'true-silence';
}

function isSamplerThrottled(stats: RecordingSessionStats): boolean {
  const rateThrottled =
    stats.durationMs > MIN_DURATION_FOR_RATE_CHECK_MS &&
    stats.effectiveSampleRate < MIN_EFFECTIVE_SAMPLE_RATE;
  const mostlyBackgrounded =
    stats.durationMs > 0 && stats.backgroundedMs > BACKGROUND_RATIO_THRESHOLD * stats.durationMs;
  return rateThrottled || mostlyBackgrounded;
}

export function useRecordingMonitor(options: RecordingMonitorOptions = {}) {
  const audioInputLevel = ref<number>(0);

  let stats = createEmptyStats();
  let sumAudioLevel = 0;
  let silentSampleCount = 0;
  let chunkIndex = 0;
  let audioLevelMonitor: AudioLevelMonitor | undefined;

  // Stored references for cleanup
  let attachedTrack: MediaStreamTrack | undefined;
  let attachedRecorder: MediaRecorder | undefined;
  let trackMuteHandler: (() => void) | undefined;
  let recorderErrorHandler: ((e: Event) => void) | undefined;
  let recorderDataHandler: ((e: BlobEvent) => void) | undefined;
  let recorderStopHandler: (() => void) | undefined;
  let visibilityHandler: (() => void) | undefined;

  let startedAt: number | undefined;
  let stoppedAt: number | undefined;
  let hiddenSince: number | undefined;

  function attach(ctx: RecordingMonitorContext): void {
    // Reset
    stats = createEmptyStats();
    sumAudioLevel = 0;
    silentSampleCount = 0;
    chunkIndex = 0;
    audioInputLevel.value = 0;
    startedAt = Date.now();
    stoppedAt = undefined;
    hiddenSince = undefined;

    // Capture device info
    const track = ctx.stream.getAudioTracks()[0];
    if (track) {
      stats.deviceLabel = track.label;
      stats.deviceSettings = track.getSettings();
    }
    stats.requestedDeviceId = ctx.requestedDeviceId;
    stats.availableDevices = ctx.availableDevices;

    // Attach event listeners
    attachedTrack = track;
    attachedRecorder = ctx.recorder;

    if (track) {
      trackMuteHandler = () => {
        stats.trackMuteEvents += 1;
      };
      track.addEventListener('mute', trackMuteHandler);
    }

    recorderErrorHandler = (event: Event) => {
      stats.recorderErrorEvents += 1;
      options.onRecorderError?.(event);

      Sentry.captureMessage(`Meeting ${ctx.meetingId} - MediaRecorder error - ${event}`, {
        level: 'error',
        tags: { 'meeting.id': ctx.meetingId },
        contexts: {
          recording: {
            deviceLabel: stats.deviceLabel,
            deviceId: stats.deviceSettings?.deviceId ?? null,
            sampleRate: stats.deviceSettings?.sampleRate ?? null,
            channelCount: stats.deviceSettings?.channelCount ?? null,
            echoCancellation: stats.deviceSettings?.echoCancellation ?? null,
            noiseSuppression: stats.deviceSettings?.noiseSuppression ?? null,
            autoGainControl: stats.deviceSettings?.autoGainControl ?? null,
            userAgent: navigator.userAgent,
          },
        },
      });
    };
    ctx.recorder.addEventListener('error', recorderErrorHandler);

    recorderDataHandler = (e: Event) => {
      const blobEvent = e as BlobEvent;
      const currentIndex = chunkIndex++;
      if (blobEvent.data.size === 0) {
        stats.emptyChunkCount += 1;
        Sentry.logger.error(
          Sentry.logger
            .fmt`Meeting ${ctx.meetingId} - empty chunk - index=${currentIndex} device="${stats.deviceLabel}"`,
        );
        options.onEmptyChunk?.(currentIndex);
      }
    };
    ctx.recorder.addEventListener('dataavailable', recorderDataHandler);

    recorderStopHandler = () => detach();
    ctx.recorder.addEventListener('stop', recorderStopHandler, { once: true });

    if (typeof document !== 'undefined') {
      if (document.visibilityState === 'hidden') {
        hiddenSince = Date.now();
        stats.visibilityHiddenCount += 1;
      }
      visibilityHandler = () => {
        if (document.visibilityState === 'hidden') {
          hiddenSince = Date.now();
          stats.visibilityHiddenCount += 1;
        } else if (hiddenSince !== undefined) {
          stats.backgroundedMs += Date.now() - hiddenSince;
          hiddenSince = undefined;
        }
      };
      document.addEventListener('visibilitychange', visibilityHandler);
    }

    // Start audio level monitoring
    audioLevelMonitor = new AudioLevelMonitor({
      fftSize: 256,
      smoothingTimeConstant: 0.3,
      decayRate: 0.05,
      gain: 2.5,
    });

    audioLevelMonitor.start(ctx.stream, (level: number) => {
      audioInputLevel.value = level;
      stats.sampleCount += 1;
      sumAudioLevel += level;
      if (level > stats.maxAudioLevel) {
        stats.maxAudioLevel = level;
      }
      if (level < SILENCE_LEVEL_THRESHOLD) {
        silentSampleCount += 1;
      }
    });
  }

  function detach(): void {
    // Freeze the recording duration at stop time (getStats may run later, after
    // the final chunk uploads, so we must not keep counting until then).
    if (stoppedAt === undefined) {
      stoppedAt = Date.now();
    }
    // Close out an open backgrounded interval (tab still hidden at stop).
    if (hiddenSince !== undefined) {
      stats.backgroundedMs += stoppedAt - hiddenSince;
      hiddenSince = undefined;
    }

    // Stop audio level monitor
    if (audioLevelMonitor) {
      audioLevelMonitor.stop();
      audioLevelMonitor = undefined;
    }

    // Remove listeners
    if (attachedTrack && trackMuteHandler) {
      attachedTrack.removeEventListener('mute', trackMuteHandler);
    }
    if (attachedRecorder) {
      if (recorderErrorHandler) {
        attachedRecorder.removeEventListener('error', recorderErrorHandler);
      }
      if (recorderDataHandler) {
        attachedRecorder.removeEventListener('dataavailable', recorderDataHandler);
      }
      if (recorderStopHandler) {
        attachedRecorder.removeEventListener('stop', recorderStopHandler);
      }
    }
    if (visibilityHandler && typeof document !== 'undefined') {
      document.removeEventListener('visibilitychange', visibilityHandler);
    }

    attachedTrack = undefined;
    attachedRecorder = undefined;
    trackMuteHandler = undefined;
    recorderErrorHandler = undefined;
    recorderDataHandler = undefined;
    recorderStopHandler = undefined;
    visibilityHandler = undefined;

    // Clear Sentry scope
    Sentry.setTag('meeting.id', undefined);
    Sentry.setContext('recording', null);
  }

  function getStats(): RecordingSessionStats {
    const endTime = stoppedAt ?? Date.now();
    const durationMs = startedAt !== undefined ? endTime - startedAt : 0;
    const effectiveSampleRate = durationMs > 0 ? stats.sampleCount / (durationMs / 1000) : 0;
    return {
      ...stats,
      meanAudioLevel: stats.sampleCount > 0 ? sumAudioLevel / stats.sampleCount : 0,
      silenceRatio: stats.sampleCount > 0 ? silentSampleCount / stats.sampleCount : 1,
      durationMs,
      effectiveSampleRate,
    };
  }

  function silenceVerdict(): {
    isSilent: boolean;
    cause: SilenceCause;
    stats: RecordingSessionStats;
  } {
    const currentStats = getStats();
    const isSilent =
      currentStats.maxAudioLevel < SILENCE_LEVEL_THRESHOLD ||
      currentStats.silenceRatio > SILENCE_RATIO_THRESHOLD;
    const cause = classifySilence(currentStats);
    return { isSilent, cause, stats: currentStats };
  }

  return { audioInputLevel, attach, detach, getStats, silenceVerdict };
}
