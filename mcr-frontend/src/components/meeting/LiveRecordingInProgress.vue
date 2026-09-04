<template>
  <template v-if="!isSendingLastAudioChunks">
    <DsfrTag
      :label="statusLabel"
      :class="
        isRecording
          ? 'rounded-sm bg-warning-950 text-warning-425'
          : 'rounded-sm bg-info-950 text-info-425'
      "
      icon="fr-icon-circle-fill"
    />
    <div class="flex flex-row items-center gap-2">
      <AudioLevelMeter :level="audioInputLevel" />
      <h2 class="text-2xl/8 font-bold">
        {{ leftPad(time.hours.value) }}:{{ leftPad(time.minutes.value) }}:{{
          leftPad(time.seconds.value)
        }}
      </h2>
    </div>
    <p class="text-grey-425 text-sm">
      {{ $t('meeting-v2.recording.device.label') }}&nbsp;: {{ currentDeviceLabel }}
    </p>
    <div class="recording-actions flex w-full flex-row justify-center gap-4">
      <DsfrButton
        v-if="isRecording"
        secondary
        :label="$t('meeting-v2.recording.buttons.pause')"
        icon="fr-icon-pause-circle-fill"
        @click="pauseRecording"
      />
      <DsfrButton
        v-else
        secondary
        :label="$t('meeting-v2.recording.buttons.resume')"
        icon="fr-icon-play-circle-fill"
        @click="resumeRecording"
      />
      <DsfrButton
        :label="$t('meeting-v2.recording.buttons.stop')"
        icon="fr-icon-stop-circle-fill"
        :disabled="effectiveOffline"
        @click="onClickStop"
      />
    </div>
  </template>
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
import EndLiveMeetingModal from '@/components/meeting/modals/EndLiveMeetingModal.vue';
import { leftPad } from '@/services/meetings/meetings-datetime';
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
  availableDevices,
  currentDeviceId,
  audioInputLevel,
  effectiveOffline,
  statusLabel,
  pauseRecording,
  resumeRecording,
  stopRecording,
} = useRecordingSession(props.meetingId);

const currentDeviceLabel = computed(
  () =>
    availableDevices.value.find((device) => device.deviceId === currentDeviceId.value)?.label ||
    t('meeting-v2.recording.device.unknown'),
);

const { open: openEndLiveMeetingModal } = useModal({
  component: EndLiveMeetingModal,
  attrs: {
    onSuccess: () => stopRecording(),
  },
});

function onClickStop() {
  pauseRecording();
  openEndLiveMeetingModal();
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
</script>

<style scoped>
:deep(.recording-actions .fr-btn::before) {
  --icon-size: 1.5rem;
}
</style>
