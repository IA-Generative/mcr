<template>
  <div class="flex flex-col items-center">
    <div class="flex justify-center items-center w-16 h-16 m-8 relative">
      <span class="fr-icon-mic-fill z-30 relative text-white fr-icon--md"></span>
      <div
        class="rounded-full bg-primary flex justify-center items-center w-full h-full absolute inset-0"
      >
        <div class="rounded-full bg-primary w-full h-full animate-ping-slow opacity-30"></div>
      </div>
    </div>

    <DsfrButton
      no-outline
      secondary
      size="large"
      @click="() => openStopCaptureModal()"
    >
      {{ $t('meeting.transcription.stop') }}
      <VIcon
        v-if="isPending"
        name="ri-loader-3-line"
        animation="spin"
      />
    </DsfrButton>
  </div>
</template>

<script setup lang="ts">
import { useModal } from 'vue-final-modal';
import { useI18n } from 'vue-i18n';
import BaseModal from '@/components/core/BaseModal.vue';
import { useMeetings } from '@/services/meetings/use-meeting';

const props = defineProps<{
  meetingId: number;
}>();

const { t } = useI18n();
const { stopCaptureMutation } = useMeetings();
const { mutate: stopCapture, isPending } = stopCaptureMutation();

const { open: openStopCaptureModal } = useModal({
  component: BaseModal,
  attrs: {
    title: t('meeting.transcription.modal-stop.title'),
    isAlert: true,
    onSuccess: () => stopCapture(props.meetingId),
  },
});
</script>
