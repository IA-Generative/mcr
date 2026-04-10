<template>
  <TableActions
    :on-delete="() => deleteMeetingModal(typedCell.id)"
    :on-edit="() => editMeetingModal(typedCell.id)"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { MeetingDto, UpdateMeetingDto } from '@/services/meetings/meetings.types';
import { useModal } from 'vue-final-modal';
import EditMeetingModal from '@/components/meeting/modals/EditMeetingModal.vue';
import DeleteMeetingModal from '@/components/meeting/modals/DeleteMeetingModal.vue';
import { useMeetings } from '@/services/meetings/use-meeting';
import { useI18n } from 'vue-i18n';

const props = defineProps<{ cell: unknown }>();

const typedCell = computed(() => props.cell as MeetingDto);
const { t } = useI18n();
const { updateMeetingMutation, deleteMeetingMutation } = useMeetings();
const { mutate: updateMeeting } = updateMeetingMutation();
const { mutate: deleteMeeting } = deleteMeetingMutation();

function editMeetingModal(id: number) {
  const { open } = useModal({
    component: EditMeetingModal,
    attrs: {
      itemSelected: typedCell.value,
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
