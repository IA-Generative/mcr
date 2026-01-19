<template>
  <div class="fr-container py-5 flex flex-col h-full">
    <div v-if="meeting">
      <div class="flex flex-row items-center justify-between">
        <MeetingFrontMatter
          :name="meeting.name"
          :name-platform="meeting.name_platform"
          :start-date="meeting.creation_date"
        />

        <div class="flex gap-3">
          <DsfrButton
            secondary
            icon="ri-edit-line"
            @click="() => openEditMeetingModal()"
          >
            {{ $t('meeting.edit') }}
          </DsfrButton>
          <DsfrButton
            secondary
            icon="ri-delete-bin-5-line"
            @click="() => openDeleteMeetingModal()"
          >
            {{ $t('meeting.delete') }}
          </DsfrButton>
        </div>
      </div>

      <TranscriptionContainer
        :meeting
        class="w-full"
      />
    </div>
    <div
      v-else-if="isLoading"
      class="flex items-center justify-center h-full"
    >
      <VIcon
        name="ri-loader-3-line"
        animation="spin"
        scale="3"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { type UpdateMeetingDto } from '@/services/meetings/meetings.types';
import EditMeetingModal from '@/components/meeting/modals/EditMeetingModal.vue';

import { useMeetings } from '@/services/meetings/use-meeting';
import { ROUTES } from '@/router/routes';
import { useModal } from 'vue-final-modal';
import { useI18n } from 'vue-i18n';
import DeleteMeetingModal from '@/components/meeting/modals/DeleteMeetingModal.vue';
import { useRecorder } from '@/composables/use-recorder';
import { is403Error, is404Error } from '@/services/http/http.utils';

const router = useRouter();
const route = useRoute();
const { t } = useI18n();
const { id } = route.params;

const { getMeetingQuery, updateMeetingMutation, deleteMeetingMutation } = useMeetings();
const { data: meeting, error, isError, isLoading } = getMeetingQuery(Number(id as string));
const { mutate: updateMeeting } = updateMeetingMutation();
const { mutate: deleteMeeting } = deleteMeetingMutation();

const { abortRecording } = useRecorder();

watch(isError, () => {
  if (isError.value && (is403Error(error.value) || is404Error(error.value))) {
    router.push({ name: ROUTES.NOT_FOUND.name });
    return;
  }
});

function openEditMeetingModal() {
  if (meeting.value === undefined) return;
  const { open: _openEdit } = useModal({
    component: EditMeetingModal,
    attrs: {
      itemSelected: meeting.value,
      onUpdateMeeting: (values: UpdateMeetingDto) =>
        updateMeeting({
          id: meeting.value.id,
          payload: values,
        }),
    },
  });

  _openEdit();
}

function openDeleteMeetingModal() {
  if (meeting.value === undefined) return;
  const { open: _openEdit } = useModal({
    component: DeleteMeetingModal,
    attrs: {
      title: t('meeting.confirm-delete.title'),
      onSuccess: () => {
        deleteMeeting(meeting.value.id);
        abortRecording();
        router.replace(ROUTES.MEETINGS.path);
      },
    },
  });

  _openEdit();
}
</script>
