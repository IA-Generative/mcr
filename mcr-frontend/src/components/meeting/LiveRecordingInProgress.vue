<template>
  <div
    v-if="!isSendingLastAudioChunks"
    class="flex flex-col items-center gap-5"
  >
    <h2 class="font-bold text-3xl/10 text-blue-france-sun">
      {{ $t('meeting-v2.recording.title') }}
    </h2>
    <DsfrTag
      :label="statusLabel"
      :class="
        isRecording
          ? 'bg-warning-950 text-warning-425 rounded'
          : 'bg-info-950 text-info-425 rounded'
      "
      icon="fr-icon-circle-fill"
    />
    <div class="flex flex-row items-center gap-2">
      <AudioLevelMeter :level="audioInputLevel" />
      <h2 class="font-bold text-2xl/8">
        {{ leftPad(time.hours.value) }}:{{ leftPad(time.minutes.value) }}:{{
          leftPad(time.seconds.value)
        }}
      </h2>
    </div>
    <div class="recording-actions flex flex-row w-full gap-4 justify-center">
      <DsfrButton
        v-if="isRecording"
        secondary
        :label="$t('meeting-v2.recording.buttons.pause')"
        icon="fr-icon-pause-circle-fill"
        @click="() => pauseRecording()"
      />
      <DsfrButton
        v-else
        secondary
        :label="$t('meeting-v2.recording.buttons.resume')"
        icon="fr-icon-play-circle-fill"
        @click="() => resumeRecording()"
      />
      <DsfrButton
        :label="$t('meeting-v2.recording.buttons.stop')"
        icon="fr-icon-stop-circle-fill"
        :disabled="effectiveOffline"
        @click="() => onClickStop()"
      />
    </div>
    <a
      href=""
      class="fr-link fr-link--sm fr-link--icon-left fr-icon-question-line self-end mr-4"
      @click.prevent="openAdvicesModal"
      >{{ $t('meeting-v2.recording.advices.title') }}</a
    >
  </div>
  <div
    v-else
    class="text-blue-france-sun"
  >
    <VIcon
      name="ri-loader-3-line"
      color="currentColor"
      animation="spin"
      scale="3"
    />
  </div>
</template>

<script lang="ts" setup>
import BaseModal from '@/components/core/BaseModal.vue';
import AudioLevelMeter from '@/components/core/AudioLevelMeter.vue';
import { useRecordingSession } from '@/composables/use-recording-session';
import LiveMeetingAdvicesModal from '@/components/meeting/modals/LiveMeetingAdvicesModal.vue';
import { useLeaveGuard } from '@/composables/use-leave-guard';
import { useModal } from 'vue-final-modal';
import { t } from '@/plugins/i18n';

const props = defineProps<{
  meetingId: number;
}>();

const {
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
} = useRecordingSession(props.meetingId);

const { open: openConfirmStopModal } = useModal({
  component: BaseModal,
  attrs: {
    title: t('meeting.transcription.recording.confirm-modal.title'),
    ctaLabel: t('meeting.transcription.recording.confirm-modal.button'),
    onSuccess: () => stopRecording(),
  },
});

const { open: openAdvicesModal } = useModal({
  component: LiveMeetingAdvicesModal,
});

function onClickStop() {
  pauseRecording();
  openConfirmStopModal();
}

function confirmAndNavigate(): Promise<boolean> {
  return new Promise((resolve) => {
    const { open: openConfirmLeaveModal } = useModal({
      component: BaseModal,
      attrs: {
        title: t('meeting.transcription.recording.confirm-quit.title'),
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

useLeaveGuard({ isInactive, confirm: confirmAndNavigate });

function leftPad(value: number): string {
  return value.toString().padStart(2, '0');
}
</script>

<style scoped>
:deep(.recording-actions .fr-btn::before) {
  --icon-size: 1.5rem;
}
</style>
