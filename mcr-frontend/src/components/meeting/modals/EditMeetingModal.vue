<template>
  <BaseModal
    :modal-id="MEETING_EDIT_MODAL_ID"
    :title="$t('meeting.modal.title')"
    size="lg"
    no-actions
  >
    <template #default>
      <AddMeetingForm
        v-if="itemSelected && isOnlineMeeting(itemSelected)"
        :initial-values="itemSelected"
        @submit="(values: UpdateMeetingDto) => onSubmitEdit(values)"
      >
        <template #actions="{ disabled }">
          <div class="flex justify-end gap-5">
            <DsfrButton
              tertiary
              no-outline
              type="button"
              @click.prevent="close"
              >{{ $t('common.cancel') }}</DsfrButton
            >
            <DsfrButton
              :disabled="disabled"
              type="submit"
              >{{ $t('meeting.form.update') }}</DsfrButton
            >
          </div>
        </template>
      </AddMeetingForm>
      <EditNameMeetingForm
        v-else-if="itemSelected && (isRecordMeeting(itemSelected) || isImportMeeting(itemSelected))"
        :initial-values="itemSelected"
        @submit="(values: UpdateMeetingDto) => onSubmitEdit(values)"
        @cancel="close"
      />
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import {
  isOnlineMeeting,
  isImportMeeting,
  isRecordMeeting,
  type UpdateMeetingDto,
  type MeetingDto,
} from '@/services/meetings/meetings.types';
import { useVfm } from 'vue-final-modal';

const MEETING_EDIT_MODAL_ID = 'meeting-edit-modal';
const close = () => useVfm().close(MEETING_EDIT_MODAL_ID);

defineProps<{
  itemSelected?: MeetingDto;
}>();

const emit = defineEmits<{ (e: 'updateMeeting', payload: UpdateMeetingDto): void }>();

function onSubmitEdit(values: UpdateMeetingDto) {
  emit('updateMeeting', values);
  close();
}
</script>
