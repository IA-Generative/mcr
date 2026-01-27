<template>
  <div class="flex flex-col items-center gap-5">
    <DsfrButton
      size="large"
      @click="() => openStartCaptureModal()"
    >
      {{ $t('meeting.transcription.start') }}
      <VIcon
        v-if="isPending"
        name="ri-loader-3-line"
        animation="spin"
      />
    </DsfrButton>
  </div>
</template>

<script lang="ts" setup>
import { useModal } from 'vue-final-modal';
import { useI18n } from 'vue-i18n';
import BaseModal from '@/components/core/BaseModal.vue';
import { useMeetings } from '@/services/meetings/use-meeting';

const props = defineProps<{
  meetingId: number;
}>();

const { t } = useI18n();

const { startCaptureMutation } = useMeetings();
const { mutate: startCapture, isPending } = startCaptureMutation();

const { open: openStartCaptureModal } = useModal({
  component: BaseModal,
  attrs: {
    title: t('meeting.transcription.modal-start.title'),
    text: t('meeting.transcription.modal-start.description'),
    isAlert: true,
    onSuccess: () => startCapture(props.meetingId),
  },
});
</script>
