<template>
  <div class="flex flex-col flex-1">
    <div class="fr-container py-5 flex flex-col">
      <div v-if="meeting">
        <div class="flex flex-row items-center justify-between">
          <MeetingFrontMatterV2 :meeting="meeting" />

          <div class="flex gap-4">
            <DsfrButton
              secondary
              icon="ri-edit-line"
              @click="() => openEditMeetingModal()"
            >
              {{ $t('meeting-v2.edit') }}
            </DsfrButton>
            <DsfrButton
              secondary
              icon="ri-delete-bin-5-line"
              @click="() => openDeleteMeetingModal()"
            >
              {{ $t('meeting-v2.delete') }}
            </DsfrButton>
          </div>
        </div>
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

    <div class="content-container flex-1">
      <div class="fr-container py-5 flex flex-col h-full">
        <div v-if="meeting">
          <MeetingPageAlert />

          <div class="grid grid-cols-2 max-sm:grid-cols-1 gap-6 mt-6">
            <MeetingAudioCard
              :meeting-id="meeting.id"
              :creation-date="meeting.creation_date"
              :status="meeting.status"
            />
          </div>
        </div>
        <div
          v-if="meeting && isRecordingLocally"
          class="mt-6 py-5 bg-grey-1000"
        >
          <LiveRecordingInProgress :meeting-id="meeting.id" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import DeleteMeetingModal from '@/components/meeting/modals/DeleteMeetingModal.vue';
import EditMeetingModal from '@/components/meeting/modals/EditMeetingModal.vue';
import { useRecorder } from '@/composables/use-recorder';
import { t } from '@/plugins/i18n';
import { ROUTES } from '@/router/routes';
import { is403Error, is404Error } from '@/services/http/http.utils';
import type { UpdateMeetingDto } from '@/services/meetings/meetings.types';
import { useMeetings } from '@/services/meetings/use-meeting';
import { useModal } from 'vue-final-modal';
import MeetingPageAlert from './MeetingPageAlert.vue';

const router = useRouter();
const route = useRoute();
const { id } = route.params;

const { getMeetingQuery, updateMeetingMutation, deleteMeetingMutation } = useMeetings();
const { data: meeting, error, isError, isLoading } = getMeetingQuery(Number(id as string));
const { mutate: updateMeeting } = updateMeetingMutation();
const { mutateAsync: deleteMeeting } = deleteMeetingMutation();

const { abortRecording } = useRecorder();

const isRecordingLocally = computed(
  () =>
    meeting?.value?.status === 'CAPTURE_IN_PROGRESS' &&
    meeting?.value?.name_platform === 'MCR_RECORD',
);
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
      onSuccess: async () => {
        abortRecording();
        await deleteMeeting(meeting.value.id);
        router.replace(ROUTES.MEETINGS.path);
      },
    },
  });

  _openEdit();
}
</script>

<style scoped>
.content-container {
  background-color: var(--beige-gris-galet-950-100);
}
</style>
