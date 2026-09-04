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
    <div
      v-if="hasNoAudioSignal"
      role="alert"
      class="w-full px-4"
    >
      <DsfrAlert
        type="error"
        :title="$t('meeting-v2.recording.no-signal.title')"
        :description="$t('meeting-v2.recording.no-signal.description')"
        title-tag="h3"
      />
      <DsfrButton
        v-if="!isNoSignalAlertMuted"
        tertiary
        no-outline
        :label="$t('meeting-v2.recording.no-signal.mute')"
        @click="muteNoSignalAlert"
      />
    </div>
    <div class="flex flex-row items-center gap-2">
      <AudioLevelMeter :level="audioInputLevel" />
      <h2 class="text-2xl/8 font-bold">
        {{ leftPad(time.hours.value) }}:{{ leftPad(time.minutes.value) }}:{{
          leftPad(time.seconds.value)
        }}
      </h2>
    </div>
    <DsfrSelect
      v-model="selectedDeviceId"
      class="w-full max-w-xs"
      :label="$t('meeting-v2.recording.device.label')"
      border-bottom
      :options="deviceOptions"
      @update:model-value="onSelectDevice"
    />
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
  hasNoAudioSignal,
  isNoSignalAlertMuted,
  effectiveOffline,
  statusLabel,
  muteNoSignalAlert,
  switchAudioDevice,
  pauseRecording,
  resumeRecording,
  stopRecording,
} = useRecordingSession(props.meetingId);

const selectedDeviceId = ref(currentDeviceId.value);
watch(currentDeviceId, (deviceId) => (selectedDeviceId.value = deviceId));

// A device plugged in mid-session can still carry an empty label: without the fallback
// it would render as a blank option.
const deviceOptions = computed(() =>
  availableDevices.value.map((device) => ({
    value: device.deviceId,
    text: device.label || t('meeting-v2.recording.device.unknown'),
  })),
);

async function onSelectDevice(deviceId: string | number) {
  await switchAudioDevice(String(deviceId));
  // Realign with the recorder: a failed switch leaves currentDeviceId untouched, and
  // Vue would not patch the select back on its own.
  selectedDeviceId.value = currentDeviceId.value;
}

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
