import { useRecorder } from '@/composables/use-recorder';
import { useRecordingMonitor, SILENCE_MESSAGES } from '@/composables/use-recording-monitor';
import { useNetworkStatus } from '@/composables/use-network-status';
import { useAudioChunkStore } from '@/composables/use-audio-chunk-store';
import { useChunkUpload } from '@/composables/use-chunk-upload';
import { useAudioChunkCleanup } from '@/composables/use-audio-chunk-cleanup';
import { useMeetings } from '@/services/meetings/use-meeting';
import { t } from '@/plugins/i18n';
import useToaster from '@/composables/use-toaster';
import * as Sentry from '@sentry/vue';

export function useRecordingSession(meetingId: number) {
  const {
    time,
    isRecording,
    isInactive,
    startRecording,
    resumeRecording,
    stopRecording,
    pauseRecording,
  } = useRecorder();

  const toaster = useToaster();
  const recordingMonitor = useRecordingMonitor({ onEmptyChunk: handleEmptyChunk });
  const audioInputLevel = recordingMonitor.audioInputLevel;

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
          trackMutedAtStop: stats.trackMutedAtStop,
          trackEndedAtStop: stats.trackEndedAtStop,
          permissionRevokedEvents: stats.permissionRevokedEvents,
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
    const totalAlreadyRecordedChunks = await getChunkCountForMeeting(meetingId).catch(() => 0);

    const pending = await getPendingChunksForMeeting(meetingId).catch(() => []);
    if (pending.length > 0 && isOnline.value) {
      uploadPendingFromIdb();
    }

    try {
      await startRecording({
        onDataAvailableHandler: (e) => handleDataChunkEvent(e),
        onStopEventHandler: () => handleOnStopEvent(),
        onRecordingStart: (ctx) => recordingMonitor.attach({ ...ctx, meetingId }),
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

  return {
    time,
    isRecording,
    isInactive,
    isSendingLastAudioChunks,
    audioInputLevel,
    effectiveOffline,
    statusLabel,
    pauseRecording,
    resumeRecording,
    stopRecording,
  };
}
