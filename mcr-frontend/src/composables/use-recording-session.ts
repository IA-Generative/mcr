import { useRecorder, type AudioDeviceInfo } from '@/composables/use-recorder';
import { useRecordingMonitor, SILENCE_MESSAGES } from '@/composables/use-recording-monitor';
import { useNetworkStatus } from '@/composables/use-network-status';
import { useAudioChunkStore } from '@/composables/use-audio-chunk-store';
import { useChunkUpload } from '@/composables/use-chunk-upload';
import { useAudioChunkCleanup } from '@/composables/use-audio-chunk-cleanup';
import { useMeetings } from '@/services/meetings/use-meeting';
import { t } from '@/plugins/i18n';
import useToaster from '@/composables/use-toaster';
import { closeAlertAudio, playNoSignalAlert } from '@/utils/audio-alert';
import { LIVE_NO_SIGNAL_MAX_BEEPS, LIVE_NO_SIGNAL_REPEAT_MS } from '@/config/audioMonitor';
import * as Sentry from '@sentry/vue';

export function useRecordingSession(meetingId: number) {
  const {
    time,
    isRecording,
    isInactive,
    currentAudioId,
    listAudioInputDevices,
    startRecording,
    switchAudioDevice: switchRecorderAudioDevice,
    resumeRecording,
    stopRecording,
    pauseRecording,
  } = useRecorder();

  const toaster = useToaster();
  const recordingMonitor = useRecordingMonitor({ onEmptyChunk: handleEmptyChunk });
  const audioInputLevel = recordingMonitor.audioInputLevel;
  const hasNoAudioSignal = recordingMonitor.hasNoAudioSignal;

  const { isOnline } = useNetworkStatus();
  const effectiveOffline = computed(() => !isOnline.value);

  const { startTranscriptionMutation, getMeetingQuery } = useMeetings();
  const { mutate: startTranscription } = startTranscriptionMutation();
  const { data: meetingQueryData } = getMeetingQuery(meetingId);
  const { cleanupMeetingChunks } = useAudioChunkCleanup();

  const { getChunkCountForMeeting, getPendingChunksForMeeting } = useAudioChunkStore();
  const { saveAndEnqueueUpload, uploadPendingFromIdb, waitForAllUploads } =
    useChunkUpload(meetingId);

  const isSendingLastAudioChunks = ref(false);

  const statusLabel = computed(() =>
    isRecording.value
      ? t('meeting-v2.recording.status.in-progress').toUpperCase()
      : t('meeting-v2.recording.status.paused').toUpperCase(),
  );

  const availableDevices = ref<AudioDeviceInfo[]>([]);
  const currentDeviceId = computed(() => currentAudioId.value ?? '');
  let hasDeviceBaseline = false;

  function describeDevice(device: AudioDeviceInfo) {
    return device.label || t('meeting-v2.recording.device.unknown');
  }

  async function refreshAvailableDevices() {
    availableDevices.value = await listAudioInputDevices().catch(() => []);
  }

  async function handleDeviceChange() {
    const previous = availableDevices.value;
    await refreshAvailableDevices();

    // Until the recorder has enumerated with the permission granted, the list carries no labels
    // and may be incomplete: diffing it would announce devices that were already there.
    if (!hasDeviceBaseline) return;

    const previousIds = new Set(previous.map((device) => device.deviceId));
    const currentIds = new Set(availableDevices.value.map((device) => device.deviceId));
    // Diffing on deviceId, not on labels: Chromium renames its `default` pseudo-device when the
    // system default moves, which a label diff would announce as a phantom device.
    const connected = availableDevices.value.filter((device) => !previousIds.has(device.deviceId));
    const disconnected = previous.filter((device) => !currentIds.has(device.deviceId));

    for (const device of connected) {
      toaster.addInfoMessage(
        t('meeting-v2.recording.device.connected', { device: describeDevice(device) }),
      );
    }
    // One message per device: only the recorded one deserves the warning, so a batch unplug must
    // not blame the others for interrupting the recording.
    for (const device of disconnected) {
      const wasRecording = device.deviceId === currentDeviceId.value;
      const message = t(
        wasRecording
          ? 'meeting-v2.recording.device.disconnected-active'
          : 'meeting-v2.recording.device.disconnected',
        { device: describeDevice(device) },
      );
      if (wasRecording) {
        toaster.addWarningMessage(message);
      } else {
        toaster.addInfoMessage(message);
      }
    }
  }

  async function switchAudioDevice(deviceId: string) {
    try {
      await switchRecorderAudioDevice(deviceId);
    } catch (error) {
      toaster.addErrorMessage(t('meeting-v2.recording.device.switch-failed'));
      // A device unplugged between the listing and the click is expected, and the
      // recording carries on: an error-level event would pollute the prod report.
      Sentry.captureException(error, {
        level: 'warning',
        tags: {
          feature: 'recording',
          'meeting.id': meetingId,
        },
        contexts: {
          recordingDevice: {
            requestedDeviceId: deviceId,
            currentDeviceId: currentDeviceId.value,
            availableDevices: availableDevices.value.map(
              (d) => `${d.label} [deviceId=${d.deviceId}, groupId=${d.groupId}]`,
            ),
          },
        },
      });
    }
  }

  const isNoSignalAlertMuted = ref(false);
  let beepTimer: ReturnType<typeof setInterval> | undefined;
  let beepCount = 0;

  function stopBeeping() {
    if (beepTimer) clearInterval(beepTimer);
    beepTimer = undefined;
    beepCount = 0;
  }

  function muteNoSignalAlert() {
    isNoSignalAlertMuted.value = true;
    stopBeeping();
  }

  watch([hasNoAudioSignal, isRecording, isNoSignalAlertMuted], ([noSignal, recording, muted]) => {
    if (!noSignal || !recording || muted) {
      stopBeeping();
      return;
    }
    if (beepTimer) return;

    beepCount = 1;
    playNoSignalAlert();
    beepTimer = setInterval(() => {
      if (beepCount >= LIVE_NO_SIGNAL_MAX_BEEPS) {
        stopBeeping();
        return;
      }
      beepCount += 1;
      playNoSignalAlert();
    }, LIVE_NO_SIGNAL_REPEAT_MS);
  });

  let emptyChunkToastShown = false;
  function handleEmptyChunk() {
    if (emptyChunkToastShown) return;
    emptyChunkToastShown = true;
    toaster.addErrorMessage(t('meeting-v2.recording.empty-chunk'));
  }

  let chunkCounter = 0;
  let pendingChunkSave: Promise<void> = Promise.resolve();

  async function handleDataChunkEvent(e: BlobEvent) {
    Sentry.startSpan(
      {
        name: 'handleDataChunk',
        attributes: {
          'meeting.id': meetingId,
          'meeting.chunk_id': chunkCounter,
        },
      },
      async () => await handleDataChunkEventCallback(e),
    );
  }

  async function handleDataChunkEventCallback(e: BlobEvent) {
    if (e.data.size === 0) return;

    Sentry.logger.info(
      Sentry.logger.fmt`Meeting ${meetingId} - chunk ${chunkCounter} - received event`,
    );
    const timestamp = Date.now();
    const filename = `${timestamp}.weba`;
    chunkCounter += 1;

    pendingChunkSave = saveAndEnqueueUpload(e.data, filename);
    await pendingChunkSave;
  }

  async function handleOnStopEvent() {
    isSendingLastAudioChunks.value = true;
    try {
      await pendingChunkSave;
      await waitForAllUploads();
      await uploadPendingFromIdb();

      const stillPending = await getPendingChunksForMeeting(meetingId);
      if (stillPending.length > 0) {
        Sentry.logger.error(
          Sentry.logger
            .fmt`Meeting ${meetingId} - ${stillPending.length} chunks still pending after final sweep`,
        );
        toaster.addErrorMessage(t('meeting-v2.recording.upload-failed'));
        return;
      }

      const { isSilent, cause, stats } = recordingMonitor.silenceVerdict();
      if (isSilent) {
        toaster.addErrorMessage(t('meeting-v2.recording.silent-detected'));

        const silenceVerdictContext = {
          maxAudioLevel: stats.maxAudioLevel,
          silenceRatio: stats.silenceRatio,
          sampleCount: stats.sampleCount,
          durationMs: stats.durationMs,
          effectiveSampleRate: stats.effectiveSampleRate,
          backgroundedMs: stats.backgroundedMs,
          visibilityHiddenCount: stats.visibilityHiddenCount,
        };

        const recordingDeviceContext = {
          requestedDeviceId: stats.requestedDeviceId,
          receivedDeviceLabel: stats.deviceLabel,
          receivedDeviceId: stats.deviceSettings?.deviceId ?? null,
          receivedDeviceSettings: stats.deviceSettings,
          availableDevices: stats.availableDevices.map(
            (d) => `${d.label} [deviceId=${d.deviceId}, groupId=${d.groupId}]`,
          ),
          deviceMismatch:
            stats.requestedDeviceId != null &&
            stats.deviceSettings?.deviceId != null &&
            stats.requestedDeviceId !== stats.deviceSettings.deviceId,
          trackMuteEvents: stats.trackMuteEvents,
          emptyChunkCount: stats.emptyChunkCount,
          deviceChangeEvents: stats.deviceChangeEvents,
          trackEndedEvents: stats.trackEndedEvents,
          deviceLabelAtStop: stats.deviceLabelAtStop,
          deviceIdAtStop: stats.deviceIdAtStop,
          deviceSwitchedMidSession: stats.deviceSwitchedMidSession,
          deliberateDeviceSwitches: stats.deliberateDeviceSwitches,
          trackMutedAtStop: stats.trackMutedAtStop,
          permissionRevokedEvents: stats.permissionRevokedEvents,
          noSignalEpisodes: stats.noSignalEpisodes,
        };

        Sentry.captureMessage(SILENCE_MESSAGES[cause], {
          level: 'error',
          fingerprint: ['silent-recording', cause],
          tags: {
            feature: 'recording',
            'error.phase': 'start',
            'meeting.id': meetingId,
            'silence.cause': cause,
          },
          contexts: {
            silenceVerdict: silenceVerdictContext,
            recordingDevice: recordingDeviceContext,
          },
        });
      }

      startTranscription(meetingId, {
        onSuccess: () => cleanupMeetingChunks(meetingId),
      });
    } finally {
      isSendingLastAudioChunks.value = false;
    }
  }

  watch(
    () => meetingQueryData.value?.status,
    (newMeetingStatus) => {
      if (newMeetingStatus === 'TRANSCRIPTION_PENDING') {
        isSendingLastAudioChunks.value = false;
      }
    },
  );

  onMounted(async () => {
    refreshAvailableDevices();
    // The monitor listens to `devicechange` too, but only to count them for the diagnosis:
    // this one refreshes what the screen shows. Merging them would couple display to telemetry.
    navigator.mediaDevices?.addEventListener('devicechange', handleDeviceChange);

    const totalAlreadyRecordedChunks = await getChunkCountForMeeting(meetingId).catch(() => 0);

    const pending = await getPendingChunksForMeeting(meetingId).catch(() => []);
    if (pending.length > 0 && isOnline.value) {
      uploadPendingFromIdb();
    }

    try {
      await startRecording({
        onDataAvailableHandler: (e) => handleDataChunkEvent(e),
        onStopEventHandler: () => handleOnStopEvent(),
        onRecordingStart: (ctx) => {
          // Enumerated after getUserMedia, so this is the first list carrying real labels.
          availableDevices.value = ctx.availableDevices;
          hasDeviceBaseline = true;
          recordingMonitor.attach({ ...ctx, meetingId });
        },
        onDeviceSwitched: (micTrack) => recordingMonitor.onDeviceSwitched(micTrack),
        numberOfChunkAlreadyRecorded: totalAlreadyRecordedChunks,
      });
    } catch (error) {
      Sentry.captureException(error, {
        tags: {
          feature: 'recording',
          'meeting.id': meetingId,
        },
        contexts: {
          recording: {
            already_recorded_chunks: totalAlreadyRecordedChunks,
            'error.phase': 'start',
          },
        },
      });
      return;
    }

    if (totalAlreadyRecordedChunks) {
      pauseRecording();
    }
  });

  onUnmounted(() => {
    navigator.mediaDevices?.removeEventListener('devicechange', handleDeviceChange);
    stopBeeping();
    closeAlertAudio();
  });

  return {
    time,
    isRecording,
    isInactive,
    isSendingLastAudioChunks,
    availableDevices,
    currentDeviceId,
    audioInputLevel,
    hasNoAudioSignal,
    isNoSignalAlertMuted,
    effectiveOffline,
    statusLabel,
    muteNoSignalAlert,
    switchAudioDevice,
    pauseRecording,
    resumeRecording,
    stopRecording,
  };
}
