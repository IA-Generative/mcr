<template>
  <div class="flex sm:justify-between sm:flex-row justify-stretch flex-col-reverse gap-4">
    <DsfrSearchBar
      v-model="search"
      class="max-sm:self-stretch"
      @search="emit('onSearch')"
    ></DsfrSearchBar>

    <DsfrDropdown
      :main-button="{
        label: $t('meetings.table.add'),
        icon: 'ri-add-line',
        size: 'md',
      }"
      class="max-sm:self-end"
      :buttons="[
        {
          label: $t('meetings.table.actions.add-visio'),
          icon: 'ri-link',
          onClick: () => openAddMeetingModal(),
        },
        {
          label: $t('meetings.table.actions.add-import'),
          icon: 'ri-file-add-line',
          onClick: () => openImportModal(),
        },
        {
          label: $t('meetings.table.actions.add-record'),
          icon: 'ri-mic-line',
          onClick: () => openRecordModal(),
        },
      ]"
    />
  </div>
</template>

<script lang="ts" setup>
import { useMeetings } from '@/services/meetings/use-meeting';
import ImportMeetingModal from '@/components/meeting/modals/ImportMeetingModal.vue';
import RecordMeetingModal from '@/components/meeting/modals/RecordMeetingModal.vue';
import CreateMeetingModal from '@/components/meeting/modals/CreateMeetingModal.vue';
import type {
  AddImportMeetingDto,
  AddImportMeetingDtoAndFile,
  AddMeetingDto,
  AddOnlineMeetingDto,
  AddRecordMeetingDto,
} from '@/services/meetings/meetings.types';
import { useModal } from 'vue-final-modal';
import { ROUTES } from '@/router/routes';
import { useRouter } from 'vue-router';
import { getFileExtension } from '@/utils/file';
import useToaster from '@/composables/use-toaster';
import { t } from '@/plugins/i18n';
import { useMultipart } from '@/composables/use-multipart';
import { useFeatureFlag } from '@/composables/use-feature-flag';
import { isAxiosError } from 'axios';

const props = defineProps<{
  modelValue?: string;
}>();

const emit = defineEmits<{
  (e: 'onSearch'): void;
  (e: 'update:modelValue', value: string): void;
}>();

const router = useRouter();
const toaster = useToaster();

const { importMeetingMutation, addMeetingMutation, startTranscriptionMutation } = useMeetings();
const { uploadFile } = useMultipart();
const { mutate: importMeeting, isPending: isImportMeetingPending } = importMeetingMutation();
const { mutate: createMeeting } = addMeetingMutation();
const { mutate: startTranscription } = startTranscriptionMutation();

const isMultipartUploadEnabled = useFeatureFlag('multipart-file');
const isMultipartUploadPending = ref(false);

// Sync the `search` ref with `modelValue` prop and emit changes
const search = computed({
  get: () => props.modelValue ?? '',
  set: (val: string) => emit('update:modelValue', val),
});

const { open: openImportModal, close: closeImportModal } = useModal({
  component: ImportMeetingModal,
  attrs: {
    get isPending() {
      return isMultipartUploadEnabled.value
        ? isMultipartUploadPending.value
        : isImportMeetingPending.value;
    },
    onImportMeeting: async (values: AddImportMeetingDtoAndFile) =>
      await importMeetingStartTranscriptionAndRedirect(values),
  },
});

const { open: openRecordModal } = useModal({
  component: RecordMeetingModal,
  attrs: {
    onRecordMeeting: (values: AddRecordMeetingDto) => createMeetingAndRedirect(values),
  },
});

const { open: openAddMeetingModal } = useModal({
  component: CreateMeetingModal,
  attrs: {
    onCreateMeeting: (values: AddOnlineMeetingDto) => createMeetingAndRedirect(values),
  },
});

function createMeetingAndRedirect(values: AddMeetingDto) {
  createMeeting(values, {
    onSuccess: (data) => redirectToMeetingPage(data.id),
    onError: () => {
      toaster.addErrorMessage(t('error.meeting-creation')!);
    },
  });
}

function startTranscriptionAndRedirect(meetingId: number) {
  startTranscription(meetingId, {
    onSuccess: () => redirectToMeetingPage(meetingId),
  });
}

function redirectToMeetingPage(meetingId: number) {
  router.push(`${ROUTES.MEETINGS.path}/${meetingId}`);
}

async function importMeetingStartTranscriptionAndRedirect({
  dto,
  file,
}: AddImportMeetingDtoAndFile) {
  const extension = getFileExtension(file);
  const timestamp = Date.now();
  const renamedFile = new File([file], `${timestamp}.${extension}`, {
    type: file.type,
    lastModified: file.lastModified,
  });

  if (isMultipartUploadEnabled.value) {
    isMultipartUploadPending.value = true;
    try {
      await uploadFileWithMultipart(dto, renamedFile);
    } catch (error) {
      console.error(error);
      toaster.addErrorMessage(t('error.file-upload')!);
    }
    isMultipartUploadPending.value = false;
  } else {
    uploadAllFileAtOnce({ dto: dto, file: renamedFile });
  }
}

async function uploadFileWithMultipart(dto: AddImportMeetingDto, file: File): Promise<void> {
  createMeeting(dto, {
    onSuccess: async (data) => {
      await uploadFile({ meetingId: data.id, file: file });
      closeImportModal();
      startTranscriptionAndRedirect(data.id);
    },
    onError: () => {
      toaster.addErrorMessage(t('error.meeting-creation')!);
    },
  });
}

async function uploadAllFileAtOnce(payload: {
  dto: AddImportMeetingDto;
  file: File;
}): Promise<void> {
  importMeeting(payload, {
    onSuccess: (data) => {
      closeImportModal();
      startTranscriptionAndRedirect(data.meeting.id);
    },
    onError: (error) => {
      if (isAxiosError(error) && error.response?.status === 415) {
        toaster.addErrorMessage(t('meeting.import-form.errors.unsupported-format')!);
      } else {
        toaster.addErrorMessage(t('error.file-upload')!);
      }
    },
  });
}
</script>
