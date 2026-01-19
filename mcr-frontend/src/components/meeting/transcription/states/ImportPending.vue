<template>
  <div class="flex flex-col items-center mx-4">
    <div class="flex flex-col items-center">
      <img
        src="@dsfr-artwork/pictograms/system/warning.svg?url"
        role="presentation"
        class="w-22 h-22 mb-6"
      />
      <p class="text-xl font-semibold mb-4 text-[var(--blue-france-sun-113-625)]">
        {{ $t('meeting.transcription.import-failed.text') }}
      </p>
      <p class="mb-8 text-[var(--default-text-grey)]">
        {{ $t('meeting.transcription.import-failed.description') }}
      </p>
    </div>
    <DsfrButton
      icon="fr-icon-upload-line"
      :disabled="isImportPending"
      @click="openImportModal"
    >
      {{ $t('meeting.transcription.import-failed.button') }}
    </DsfrButton>
  </div>
</template>

<script lang="ts" setup>
import { useMeetings } from '@/services/meetings/use-meeting';
import ImportMeetingModal from '@/components/meeting/modals/ImportMeetingModal.vue';
import type { AddImportMeetingDtoAndFile } from '@/services/meetings/meetings.types';
import { useModal } from 'vue-final-modal';
import { getFileExtension } from '@/utils/file';
import { isAxiosError } from 'axios';
import useToaster from '@/composables/use-toaster';
import { t } from '@/plugins/i18n';

const props = defineProps<{
  meetingId: number;
  meetingName: string;
}>();

const toaster = useToaster();

const { uploadFileWithPresignedUrlMutation, updateMeetingMutation, startTranscriptionMutation } =
  useMeetings();
const { mutate: uploadMeetingFile, isPending: isImportPending } =
  uploadFileWithPresignedUrlMutation();
const { mutate: updateMeeting } = updateMeetingMutation();
const { mutate: startTranscription } = startTranscriptionMutation();

const { open: openImportModal, close: closeImportModal } = useModal({
  component: ImportMeetingModal,
  attrs: {
    get isPending() {
      return isImportPending.value;
    },
    meetingName: props.meetingName,
    onImportMeeting: (values: AddImportMeetingDtoAndFile) => {
      const updateMeetingPayload = {
        id: props.meetingId,
        payload: values.dto,
      };
      updateMeeting(updateMeetingPayload);
      importMeetingStartTranscriptionAndRedirect(values.file);
    },
  },
});

function importMeetingStartTranscriptionAndRedirect(file: File) {
  const extension = getFileExtension(file);
  const timestamp = Date.now();
  const renamedFile = new File([file], `${timestamp}.${extension}`, {
    type: file.type,
    lastModified: file.lastModified,
  });

  const payload = {
    meetingId: props.meetingId,
    file: renamedFile,
  };

  uploadMeetingFile(payload, {
    onSuccess: () => {
      closeImportModal();
      startTranscription(props.meetingId);
    },
    onError: (error) => {
      if (isAxiosError(error) && error.response?.status === 415) {
        toaster.addErrorMessage(t('meeting.import-form.errors.unsupported-format')!);
      }
    },
  });
}
</script>

<style scoped>
.fr-icon-warning-line::before {
  --icon-size: 2rem;
}
</style>
