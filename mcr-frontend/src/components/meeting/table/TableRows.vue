<template>
  <template v-if="!props.isPending || props.meetings === undefined">
    <DsfrTableRow
      v-for="meeting in meetings"
      :key="meeting.id"
    >
      <DsfrTableCell
        :field="{
          component: TableTag,
          meeting: meeting,
        }"
      >
      </DsfrTableCell>
      <DsfrTableCell
        :field="{
          component: RouterLink,
          text: meeting.name,
          to: `${ROUTES.MEETINGS.path}/${meeting.id}`,
          class: 'truncate max-w-full inline-block',
        }"
      ></DsfrTableCell>
      <DsfrTableCell
        :field="{
          text: formatMeetingDate(meeting.creation_date),
        }"
      ></DsfrTableCell>
      <DsfrTableCell
        :field="{
          component: TableActions,
          onDelete: () => deleteMeetingModal(meeting.id),
          onEdit: () => editMeetingModal(meeting.id),
        }"
      ></DsfrTableCell>
    </DsfrTableRow>
  </template>

  <template v-else>
    <DsfrTableRow
      v-for="(row, index) in skeletons({ rows: 10, cols: 4 })"
      :key="index"
    >
      <DsfrTableCell
        v-for="(col, colIndex) in row"
        :key="colIndex"
        :field="col"
      />
    </DsfrTableRow>
  </template>
</template>

<script lang="ts" setup>
import { RouterLink } from 'vue-router';
import { ROUTES } from '@/router/routes';
import { formatMeetingDate } from '@/utils/formatters';
import TableActions from '@/components/table/TableActions.vue';
import TableTag from '@/components/meeting/table/TableTag.vue';
import type { MeetingDto, UpdateMeetingDto } from '@/services/meetings/meetings.types';
import { useTable } from '@/composables/use-table';
import { useModal } from 'vue-final-modal';
import EditMeetingModal from '@/components/meeting/modals/EditMeetingModal.vue';
import { useMeetings } from '@/services/meetings/use-meeting';
import { useI18n } from 'vue-i18n';
import DeleteMeetingModal from '../modals/DeleteMeetingModal.vue';

const props = defineProps<{
  meetings?: MeetingDto[];
  isPending?: boolean;
}>();
const { t } = useI18n();
const { skeletons } = useTable({ cols: 4 });

const { updateMeetingMutation, deleteMeetingMutation } = useMeetings();
const { mutate: updateMeeting } = updateMeetingMutation();
const { mutate: deleteMeeting } = deleteMeetingMutation();

function editMeetingModal(id: number) {
  const meeting = props.meetings?.find((m) => m.id === id);
  const { open: _openEdit } = useModal({
    component: EditMeetingModal,
    attrs: {
      itemSelected: meeting,
      onUpdateMeeting: (values: UpdateMeetingDto) =>
        updateMeeting({
          id: id,
          payload: values,
        }),
    },
  });

  _openEdit();
}

function deleteMeetingModal(id: number) {
  const { open: _openEdit } = useModal({
    component: DeleteMeetingModal,
    attrs: {
      title: t('meeting.confirm-delete.title'),
      onSuccess: () => deleteMeeting(id),
    },
  });

  _openEdit();
}
</script>
