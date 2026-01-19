<template>
  <BaseModal
    :modal-id="RECORD_MODAL_ID"
    :title="$t('meeting.record-form.title')"
    size="lg"
    no-actions
  >
    <template #default>
      <RecordMeetingForm
        @submit="(values: AddRecordMeetingDto) => onSubmit(values)"
        @cancel="() => close()"
      />
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import type { AddRecordMeetingDto } from '@/services/meetings/meetings.types';
import { useVfm } from 'vue-final-modal';

const emit = defineEmits<{
  (e: 'recordMeeting', payload: AddRecordMeetingDto): void;
}>();

const RECORD_MODAL_ID = 'meeting-record-modal';

function onSubmit(values: AddRecordMeetingDto) {
  emit('recordMeeting', values);
  close();
}

function close() {
  useVfm().close(RECORD_MODAL_ID);
}
</script>
