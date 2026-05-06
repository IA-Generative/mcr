<template>
  <div
    v-if="!isSendingLastAudioChunks"
    class="flex flex-col items-center gap-5"
  >
    <div
      class="rounded-sm px-2 flex items-center gap-1"
      :class="isRecording ? 'bg-warning-950 text-warning-425' : 'bg-info-950 text-info-425'"
    >
      <VIcon
        name="ri-circle-fill"
        scale="1"
        color="currentColor"
      />
      <span class="text-base/6 font-bold text-center">
        {{ statusLabel }}
      </span>
    </div>
    <div class="flex flex-row items-center gap-2">
      <AudioLevelMeter :level="audioInputLevel" />
      <h2 class="font-bold text-2xl/8">
        {{ leftPad(time.hours.value) }}:{{ leftPad(time.minutes.value) }}:{{
          leftPad(time.seconds.value)
        }}
      </h2>
    </div>
    <div class="grid grid-cols-2 w-full max-w-xs gap-4">
      <RoundedActionButton
        v-if="!isRecording"
        icon="ri-play-circle-fill"
        @click="() => resumeRecording()"
      >
        {{ $t('meeting.transcription.recording.actions.resume') }}
      </RoundedActionButton>
      <RoundedActionButton
        v-else
        icon="ri-pause-circle-fill"
        @click="() => pauseRecording()"
      >
        {{ $t('meeting.transcription.recording.actions.pause') }}
      </RoundedActionButton>
      <RoundedActionButton
        icon="ri-stop-circle-fill"
        :disabled="effectiveOffline"
        @click="() => onClickStop()"
      >
        {{ $t('meeting.transcription.recording.actions.start-transcription') }}
      </RoundedActionButton>
    </div>
    <RecordMeetingFormNotice
      :is-online="!effectiveOffline"
      class="w-full max-w-2xl"
    />
  </div>
  <div v-else>
    <VIcon
      name="ri-loader-3-line"
      color="var(--blue-france-sun-113-625)"
      animation="spin"
      scale="3"
    />
  </div>
</template>

<script lang="ts" setup>
import BaseModal from '@/components/core/BaseModal.vue';
import RoundedActionButton from '@/components/core/RoundedActionButton.vue';
import AudioLevelMeter from '@/components/core/AudioLevelMeter.vue';
import { useRecorder } from '@/composables/use-recorder';
import { useRecordingMonitor } from '@/composables/use-recording-monitor';
import { useNetworkStatus } from '@/composables/use-network-status';
import { useFeatureFlag } from '@/composables/use-feature-flag';
import { useAudioChunkStore } from '@/composables/use-audio-chunk-store';
import { useChunkUpload } from '@/composables/use-chunk-upload';
import { useAudioChunkCleanup } from '@/composables/use-audio-chunk-cleanup';
import { leftPad } from '@/services/meetings/meetings-datetime';
import { useMeetings } from '@/services/meetings/use-meeting';
import { useModal } from 'vue-final-modal';
import { useI18n } from 'vue-i18n';
import useToaster from '@/composables/use-toaster';
import * as Sentry from '@sentry/vue';

const {
  time,
  isRecording,
  isInactive,
  startRecording,
  resumeRecording,
  stopRecording,
  pauseRecording,
} = useRecorder();
const { t } = useI18n();
const toaster = useToaster();

let emptyChunkToastShown = false;

function handleEmptyChunk() {
  if (emptyChunkToastShown) return;
  emptyChunkToastShown = true;
  toaster.addErrorMessage(t('meeting.transcription.recording.empty-chunk'));
}

const recordingMonitor = useRecordingMonitor({
  onEmptyChunk: handleEmptyChunk,
});
const audioInputLevel = recordingMonitor.audioInputLevel;
const { isOnline } = useNetworkStatus();
const isOfflineRecordingEnabled = useFeatureFlag('offline-recording');
const effectiveOffline = computed(() => isOfflineRecordingEnabled.value && !isOnline.value);

const isSendingLastAudioChunks = ref(false);

const props = defineProps<{
  meetingId: number;
}>();

const { startTranscriptionMutation, getMeetingQuery } = useMeetings();
const { mutate: startTranscription } = startTranscriptionMutation();
const { data: meetingQueryData } = getMeetingQuery(props.meetingId);
const { cleanupMeetingChunks } = useAudioChunkCleanup();

const { getChunkCountForMeeting, getPendingChunksForMeeting } = useAudioChunkStore();
const { saveAndEnqueueUpload, uploadPendingFromIdb, waitForAllUploads } = useChunkUpload(
  props.meetingId,
);

const statusLabel = computed(() =>
  isRecording.value
    ? t('meeting.transcription.recording.status.in-progress').toUpperCase()
    : t('meeting.transcription.recording.status.paused').toUpperCase(),
);

let chunkCounter = 0;
let pendingChunkSave: Promise<void> = Promise.resolve();

const { open: openConfirmStopModal } = useModal({
  component: BaseModal,
  attrs: {
    title: t('meeting.transcription.recording.confirm-modal.title'),
    ctaLabel: t('meeting.transcription.recording.confirm-modal.button'),
    onSuccess: () => {
      stopRecording();
    },
  },
});

function onClickStop() {
  pauseRecording();
  openConfirmStopModal();
}

async function handleDataChunkEvent(e: BlobEvent) {
  Sentry.startSpan(
    {
      name: 'handleDataChunk',
      attributes: {
        'meeting.id': props.meetingId,
        'meeting.chunk_id': chunkCounter,
      },
    },
    async () => await handleDataChunkEventCallback(e),
  );
}

async function handleDataChunkEventCallback(e: BlobEvent) {
  if (e.data.size === 0) return;

  Sentry.logger.info(
    Sentry.logger.fmt`Meeting ${props.meetingId} - chunk ${chunkCounter} - received event`,
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

    const stillPending = await getPendingChunksForMeeting(props.meetingId);
    if (stillPending.length > 0) {
      Sentry.logger.error(
        Sentry.logger
          .fmt`Meeting ${props.meetingId} - ${stillPending.length} chunks still pending after final sweep`,
      );
      toaster.addErrorMessage(t('meeting.transcription.recording.upload-failed'));
      return;
    }

    const { isSilent, stats } = recordingMonitor.silenceVerdict();
    if (isSilent) {
      toaster.addErrorMessage(t('meeting.transcription.recording.silent-detected'));
      Sentry.captureMessage('Silent recording detected', {
        level: 'error',
        tags: {
          feature: 'recording',
          'error.phase': 'start',
          'meeting.id': props.meetingId,
        },
        contexts: {
          silenceVerdict: {
            maxAudioLevel: stats.maxAudioLevel,
            silenceRatio: stats.silenceRatio,
            sampleCount: stats.sampleCount,
          },
        },
      });
    }

    startTranscription(props.meetingId, {
      onSuccess: () => cleanupMeetingChunks(props.meetingId),
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

function beforeUnloadHandler(e: BeforeUnloadEvent) {
  e.preventDefault();
  e.returnValue = true; // This adds support to browsers that require a return value
}

function confirmAndNavigate(): Promise<boolean> {
  return new Promise((resolve) => {
    const { open: openConfirmLeaveModal } = useModal({
      component: BaseModal,
      attrs: {
        title: t('meeting.transcription.recording.confirm-modal.title'),
        text: t('meeting.transcription.recording.confirm-quit.description'),
        closeButtonLabel: t('meeting.transcription.recording.confirm-quit.button'),
        onSuccess: () => {
          stopRecording();
          resolve(true);
        },
      },
    });

    openConfirmLeaveModal();
  });
}

onBeforeRouteLeave(async () => {
  // Allow navigation if no recording is in progress or if the user confirms
  return isInactive.value || (await confirmAndNavigate());
});

onMounted(async () => {
  window.addEventListener('beforeunload', beforeUnloadHandler);

  const totalAlreadyRecordedChunks = await getChunkCountForMeeting(props.meetingId).catch(() => 0);

  const pending = await getPendingChunksForMeeting(props.meetingId).catch(() => []);
  const hasPendingChunks = pending.length > 0;

  if (hasPendingChunks && isOnline.value) {
    uploadPendingFromIdb();
  }

  try {
    await startRecording({
      onDataAvailableHandler: (e) => handleDataChunkEvent(e),
      onStopEventHandler: () => handleOnStopEvent(),
      onRecordingStart: (ctx) => recordingMonitor.attach({ ...ctx, meetingId: props.meetingId }),
      numberOfChunkAlreadyRecorded: totalAlreadyRecordedChunks,
    });
  } catch (error) {
    Sentry.captureException(error, {
      tags: {
        feature: 'recording',
        'meeting.id': props.meetingId,
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
  window.removeEventListener('beforeunload', beforeUnloadHandler);
});
</script>
