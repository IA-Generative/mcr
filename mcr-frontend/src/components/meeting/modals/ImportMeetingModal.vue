<template>
  <BaseModal
    :modal-id="MEETING_IMPORT_MODAL_ID"
    :title="$t('meeting.import-form.title')"
    size="lg"
    class="max-sm:p-4"
    accept="[video/*, audio/*]"
    no-actions
    :disable-close-on-outside-click="isPending"
  >
    <ImportMeetingForm
      class="pt-4"
      :is-pending="isPending"
      :meeting-name="meetingName"
      @submit="(values: AddImportMeetingDtoAndFile) => onSubmitImport(values)"
      @cancel="close()"
    />
  </BaseModal>
</template>

<script setup lang="ts">
import type { AddImportMeetingDtoAndFile } from '@/services/meetings/meetings.types';
import { useVfm } from 'vue-final-modal';

defineProps<{
  isPending: boolean;
  meetingName?: string;
}>();

const emit = defineEmits<{
  (e: 'importMeeting', payload: AddImportMeetingDtoAndFile): void;
}>();

const MEETING_IMPORT_MODAL_ID = 'meeting-import-modal';
const close = () => useVfm().close(MEETING_IMPORT_MODAL_ID);

function onSubmitImport(values: AddImportMeetingDtoAndFile) {
  emit('importMeeting', values);
}
</script>
