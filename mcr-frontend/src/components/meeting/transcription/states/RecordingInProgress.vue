<template>
  <div
    v-if="!isSendingLastAudioChunks"
    class="flex flex-col items-center gap-5"
  >
    <div
      v-if="isRecording"
      class="rounded-sm px-2 flex items-center gap-1 bg-[var(--warning-950-100)]"
    >
      <VIcon
        name="ri-circle-fill"
        scale="1"
        color="var(--warning-425-625)"
      />
      <span class="text-base/6 font-bold text-center text-[var(--warning-425-625)]">
        {{ $t('meeting.transcription.recording.status.in-progress').toUpperCase() }}
      </span>
    </div>
    <div
      v-else
      class="rounded-sm px-2 flex items-center gap-1 bg-[var(--info-950-100)]"
    >
      <VIcon
        name="ri-circle-fill"
        scale="1"
        color="var(--info-425-625)"
      />
      <span class="text-base/6 font-bold text-center text-[var(--info-425-625)]">
        {{ $t('meeting.transcription.recording.status.paused').toUpperCase() }}
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
    <div class="grid grid-cols-2 w-[60%] gap-4">
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
        @click="() => onClickStop()"
      >
        {{ $t('meeting.transcription.recording.actions.stop') }}
      </RoundedActionButton>
    </div>
    <RecordMeetingFormNotice />
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
import { useLocalStorageRecording } from '@/composables/use-local-storage-recording';
import { useMeetings } from '@/services/meetings/use-meeting';
import { useModal } from 'vue-final-modal';
import { useI18n } from 'vue-i18n';
import * as Sentry from '@sentry/vue';

const {
  time,
  isRecording,
  isInactive,
  startRecording,
  resumeRecording,
  stopRecording,
  pauseRecording,
  audioInputLevel,
} = useRecorder();
const { t } = useI18n();

const isSendingLastAudioChunks = ref(false);

const props = defineProps<{
  meetingId: number;
}>();

const { startTranscriptionMutation, uploadFileWithPresignedUrlMutation, getMeetingQuery } =
  useMeetings();
const { mutate: startTranscription } = startTranscriptionMutation();
const { mutateAsync: uploadFile } = uploadFileWithPresignedUrlMutation();
const { data: meetingQueryData } = getMeetingQuery(props.meetingId);

const { saveRecordingProgress, clearRecordingProgress, loadRecordingProgress } =
  useLocalStorageRecording();

let chunkCounter = 0;

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

const pendingUploads: Promise<void>[] = [];

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
  Sentry.logger.info(
    Sentry.logger.fmt`Meeting ${props.meetingId} - chunk ${chunkCounter} - received event`,
  );
  const timestamp = Date.now();
  updateAndSaveChunkCount();
  const task = uploadFile(
    {
      meetingId: props.meetingId,
      file: new File([e.data], `${timestamp}.weba`, {
        type: 'audio/weba',
      }),
    },
    {
      onSuccess: () => {
        Sentry.logger.info(
          Sentry.logger.fmt`Meeting ${props.meetingId} - chunk ${chunkCounter} - uploaded to S3`,
        );
      },
      onError: (error: Error) => {
        Sentry.logger.error(
          Sentry.logger
            .fmt`Meeting ${props.meetingId} - chunk ${chunkCounter} - failed upload - ${error}`,
        );
      },
    },
  );
  pendingUploads.push(task);
}

async function handleOnStopEvent() {
  isSendingLastAudioChunks.value = true;
  await Promise.allSettled(pendingUploads);
  startTranscription(props.meetingId, {
    onSuccess: () => {
      clearRecordingProgress(props.meetingId);
    },
  });
}

function updateAndSaveChunkCount() {
  chunkCounter += 1;
  saveRecordingProgress(props.meetingId, chunkCounter);
}

watch(
  () => meetingQueryData.value?.status,
  (newMeetingStatus) => {
    if (newMeetingStatus === 'TRANSCRIPTION_PENDING') {
      isSendingLastAudioChunks.value = false;
    }
  },
);

function leftPad(value: number): string {
  return value.toString().padStart(2, '0');
}

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

onMounted(() => {
  window.addEventListener('beforeunload', beforeUnloadHandler);
  const alreadyRecordedChunks = loadRecordingProgress(props.meetingId);
  chunkCounter = alreadyRecordedChunks ?? 0;

  startRecording({
    onDataAvailableHandler: (e) => handleDataChunkEvent(e),
    onStopEventHandler: () => handleOnStopEvent(),
    numberOfChunkAlreadyRecorded: chunkCounter,
  });
});

onUnmounted(() => {
  window.removeEventListener('beforeunload', beforeUnloadHandler);
});
</script>
