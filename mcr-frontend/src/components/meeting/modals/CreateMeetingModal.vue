<template>
  <BaseModal
    :modal-id="CREATE_MEETING_MODAL_ID"
    :title="$t('meeting.form.title')"
    size="lg"
    class="max-sm:p-4"
    no-actions
  >
    <AddMeetingForm
      class="pt-4"
      @submit="(values: AddOnlineMeetingDto) => onSubmit(values)"
      @cancel="close"
    />
  </BaseModal>
</template>

<script setup lang="ts">
import BaseModal from '@/components/core/BaseModal.vue';
import type { AddOnlineMeetingDto } from '@/services/meetings/meetings.types';
import { useVfm } from 'vue-final-modal';
import AddMeetingForm from '../AddMeetingForm.vue';

const emit = defineEmits<{
  (e: 'createMeeting', payload: AddOnlineMeetingDto): void;
}>();

const CREATE_MEETING_MODAL_ID = 'meeting-import-modal';
const close = () => useVfm().close(CREATE_MEETING_MODAL_ID);

function onSubmit(values: AddOnlineMeetingDto) {
  emit('createMeeting', values);
  close();
}
</script>
