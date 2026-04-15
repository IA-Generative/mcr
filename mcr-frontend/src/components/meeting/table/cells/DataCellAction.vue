<template>
  <TableActions
    :on-delete="() => deleteMeetingModal(cell.id)"
    :on-edit="() => editMeetingModal(cell.id)"
  />
</template>

<script setup lang="ts">
import type { MeetingDto, UpdateMeetingDto } from '@/services/meetings/meetings.types';
import { useModal } from 'vue-final-modal';
import { t } from '@/plugins/i18n';
import EditMeetingModal from '@/components/meeting/modals/EditMeetingModal.vue';
import DeleteMeetingModal from '@/components/meeting/modals/DeleteMeetingModal.vue';
import { useMeetings } from '@/services/meetings/use-meeting';

const props = defineProps<{ cell: MeetingDto }>();
const selectedCell = computed(() => props.cell);

const { updateMeetingMutation, deleteMeetingMutation } = useMeetings();
const { mutate: updateMeeting } = updateMeetingMutation();
const { mutate: deleteMeeting } = deleteMeetingMutation();

function editMeetingModal(id: number) {
  const { open } = useModal({
    component: EditMeetingModal,
    attrs: {
      itemSelected: selectedCell.value,
      onUpdateMeeting: (values: UpdateMeetingDto) => updateMeeting({ id, payload: values }),
    },
  });
  open();
}

function deleteMeetingModal(id: number) {
  const { open } = useModal({
    component: DeleteMeetingModal,
    attrs: {
      title: t('meeting.confirm-delete.title'),
      onSuccess: () => deleteMeeting(id),
    },
  });
  open();
}
</script>
