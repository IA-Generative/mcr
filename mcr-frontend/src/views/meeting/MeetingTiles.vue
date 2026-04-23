<template>
  <div class="tile-container">
    <DsfrTile
      class="tile"
      :horizontal="true"
      :small="true"
      :img-src="videoSvgPath"
      :title="t('meetings_v2.tile-import.title')"
      :description="t('meetings_v2.tile-import.subtitle')"
      @click="openImportModal"
    />
    <DsfrTile
      class="tile"
      :horizontal="true"
      :small="true"
      :img-src="podcastSvgPath"
      :title="t('meetings_v2.tile-record.title')"
      :description="t('meetings_v2.tile-record.subtitle')"
      @click="openRecordModal"
    />
    <DsfrTile
      class="tile"
      :horizontal="true"
      :small="true"
      :img-src="selfTrainingSvgPath"
      :title="t('meetings_v2.tile-visio.title')"
      :description="
        isWebexEnabled
          ? t('meetings_v2.tile-visio.subtitle-with-webex')
          : t('meetings_v2.tile-visio.subtitle-without-webex')
      "
      @click="openVisioMeetingModal"
    />
  </div>
</template>

<script lang="ts" setup>
import CreateVisioMeetingModal from '@/components/meeting/modals/CreateVisioMeetingModal.vue';
import ImportMeetingModal from '@/components/meeting/modals/ImportMeetingModal.vue';
import RecordMeetingModal from '@/components/meeting/modals/RecordMeetingModal.vue';
import { useFeatureFlag } from '@/composables/use-feature-flag';
import { useMultipart } from '@/composables/use-multipart';
import useToaster from '@/composables/use-toaster';
import { t } from '@/plugins/i18n';
import videoSvgPath from '@dsfr-artwork/pictograms/leisure/video.svg?url';
import podcastSvgPath from '@dsfr-artwork/pictograms/leisure/podcast.svg?url';
import selfTrainingSvgPath from '@dsfr-artwork/pictograms/digital/self-training.svg?url';
import { ROUTES } from '@/router/routes';
import type {
  AddImportMeetingDto,
  AddImportMeetingDtoAndFile,
  AddMeetingDto,
  AddOnlineMeetingDto,
  AddRecordMeetingDto,
} from '@/services/meetings/meetings.types';
import { useMeetings } from '@/services/meetings/use-meeting';
import { getFileExtension } from '@/utils/file';
import { useModal } from 'vue-final-modal';

const isWebexEnabled = useFeatureFlag('webex');
const isMultipartUploadPending = ref(false);

const router = useRouter();
const toaster = useToaster();
const { addMeetingMutation, startTranscriptionMutation, startCaptureMutation } = useMeetings();
const { uploadFile } = useMultipart();
const { mutate: createMeeting, mutateAsync: createMeetingAsync } = addMeetingMutation();
const { mutate: startTranscription } = startTranscriptionMutation();
const { mutateAsync: startCaptureAsync } = startCaptureMutation();

const { open: openImportModal, close: closeImportModal } = useModal({
  component: ImportMeetingModal,
  attrs: {
    get isPending() {
      return isMultipartUploadPending.value;
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

const { open: openVisioMeetingModal } = useModal({
  component: CreateVisioMeetingModal,
  attrs: {
    onCreateMeeting: (values: AddOnlineMeetingDto) => createMeetingStartCaptureAndRedirect(values),
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

function createMeetingStartCaptureAndRedirect(values: AddMeetingDto) {
  createMeeting(values, {
    onSuccess: async (data) => {
      await startCaptureAsync(data.id);
      redirectToMeetingPage(data.id);
    },
    onError: () => {
      toaster.addErrorMessage(t('error.meeting-creation')!);
    },
  });
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

  const dtoWithDates = await updateDtoWithDates(dto, file);

  try {
    isMultipartUploadPending.value = true;
    await uploadFileWithMultipart(dtoWithDates, renamedFile);
  } catch (error) {
    console.error(error);
    toaster.addErrorMessage(t('error.file-upload')!);
  } finally {
    isMultipartUploadPending.value = false;
  }
}

function startTranscriptionAndRedirect(meetingId: number) {
  startTranscription(meetingId, {
    onSuccess: () => redirectToMeetingPage(meetingId),
  });
}

function redirectToMeetingPage(meetingId: number) {
  router.push(`${ROUTES.MEETINGS.path}/${meetingId}`);
}

async function uploadFileWithMultipart(dto: AddImportMeetingDto, file: File): Promise<void> {
  try {
    const meeting = await createMeetingAsync(dto);
    await uploadFile({ meetingId: meeting.id, file });
    closeImportModal();
    startTranscriptionAndRedirect(meeting.id);
  } catch (e) {
    toaster.addErrorMessage(t('error.meeting-creation')!);
  }
}

async function updateDtoWithDates(
  dto: AddImportMeetingDto,
  file: File,
): Promise<AddImportMeetingDto> {
  const audio = new Audio();
  audio.src = URL.createObjectURL(file);
  await new Promise((resolve) => (audio.onloadedmetadata = resolve));
  const duration = audio.duration;

  const endDate = new Date(Date.now());
  const startDate = new Date(endDate.getTime() - duration * 1000);
  dto.start_date = startDate.toISOString();
  dto.end_date = endDate.toISOString();

  return dto;
}
</script>

<style scoped>
.tile-container {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.tile {
  width: 95vw;
  height: 20vh;
}

@media (min-width: 440px) {
  .tile {
    width: 95vw;
    height: 15vh;
  }
}

@media (min-width: 1040px) {
  .tile-container {
    flex-direction: row;
  }

  .tile {
    width: 30vw;
    height: 20vh;
  }
}
</style>
