<template>
  <div class="flex flex-col gap-[18px] min-[1040px]:flex-row">
    <div :class="[tileClasses, 'relative']">
      <ActionTile
        class="size-full"
        :img-src="videoSvgPath"
        :title="t('meetings_v2.tile-import.title')!"
        :description="
          t('meetings_v2.tile-import.subtitle', { formats: ALLOWED_IMPORT_FORMATS_LABEL })!
        "
        :disabled="hasActiveUploads"
        @click="openFilePicker"
      />

      <div
        v-if="hasActiveUploads"
        class="pointer-events-none absolute inset-0 flex items-center justify-center"
      >
        <VIcon
          name="ri-loader-4-line"
          animation="spin"
          :scale="2"
        />
      </div>

      <input
        ref="fileInput"
        type="file"
        :accept="IMPORT_ACCEPT_ATTR"
        hidden
        @change="onFileSelected"
      />
    </div>

    <ActionTile
      :class="tileClasses"
      :img-src="podcastSvgPath"
      :title="t('meetings_v2.tile-record.title')!"
      :description="t('meetings_v2.tile-record.subtitle')!"
      @click="openRecordModal"
    />

    <ActionTile
      :class="tileClasses"
      :img-src="selfTrainingSvgPath"
      :title="t('meetings_v2.tile-visio.title')!"
      :description="
        isWebexEnabled
          ? t('meetings_v2.tile-visio.subtitle-with-webex')!
          : t('meetings_v2.tile-visio.subtitle-without-webex')!
      "
      @click="openVisioMeetingModal"
    />
  </div>
</template>

<script lang="ts" setup>
import ActionTile from '@/components/meeting/ActionTile.vue';
import CreateVisioMeetingModal from '@/components/meeting/modals/CreateVisioMeetingModal.vue';
import RecordMeetingModal from '@/components/meeting/modals/RecordMeetingModal.vue';
import { useFeatureFlag } from '@/composables/use-feature-flag';
import { useImportMeeting } from '@/composables/use-import-meeting';
import { useUploadStatus } from '@/composables/use-upload-status';
import useToaster from '@/composables/use-toaster';
import { t } from '@/plugins/i18n';
import videoSvgPath from '@dsfr-artwork/pictograms/leisure/video.svg?url';
import podcastSvgPath from '@dsfr-artwork/pictograms/leisure/podcast.svg?url';
import selfTrainingSvgPath from '@dsfr-artwork/pictograms/digital/self-training.svg?url';
import { ROUTES } from '@/router/routes';
import type {
  AddMeetingDto,
  AddOnlineMeetingDto,
  AddRecordMeetingDto,
} from '@/services/meetings/meetings.types';
import { useMeetings } from '@/services/meetings/use-meeting';
import { ALLOWED_IMPORT_FORMATS_LABEL, IMPORT_ACCEPT_ATTR } from '@/utils/file';
import { useModal } from 'vue-final-modal';

const tileClasses =
  'w-[95vw] h-[20vh] min-[440px]:h-[15vh] min-[1040px]:w-[30vw] min-[1040px]:h-[20vh]';

const isWebexEnabled = useFeatureFlag('webex');
const { hasActiveUploads } = useUploadStatus();
const fileInput = ref<HTMLInputElement | null>(null);

const router = useRouter();
const toaster = useToaster();
const { addMeetingMutation, startCaptureMutation } = useMeetings();
const { mutate: createMeeting } = addMeetingMutation();
const { mutateAsync: startCaptureAsync } = startCaptureMutation();
const { importFile } = useImportMeeting();

function openFilePicker() {
  fileInput.value?.click();
}

async function onFileSelected(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;

  try {
    await importFile(file);
  } finally {
    input.value = '';
  }
}

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

function redirectToMeetingPage(meetingId: number) {
  router.push(`${ROUTES.MEETINGS.path}/${meetingId}`);
}
</script>
