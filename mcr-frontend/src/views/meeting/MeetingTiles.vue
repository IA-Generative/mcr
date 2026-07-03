<template>
  <div class="flex flex-col gap-[18px] min-[1040px]:flex-row">
    <div :class="[tileClasses, 'relative']">
      <DsfrTile
        class="h-full w-full"
        :horizontal="true"
        :small="true"
        :img-src="videoSvgPath"
        :title="t('meetings_v2.tile-import.title')"
        :description="t('meetings_v2.tile-import.subtitle')"
        :disabled="isImporting"
        @click="openFilePicker"
      />
      <div
        v-if="isImporting"
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
        accept="video/*, audio/*"
        hidden
        @change="onFileSelected"
      />
    </div>
    <DsfrTile
      :class="tileClasses"
      :horizontal="true"
      :small="true"
      :img-src="podcastSvgPath"
      :title="t('meetings_v2.tile-record.title')"
      :description="t('meetings_v2.tile-record.subtitle')"
      @click="openRecordModal"
    />
    <DsfrTile
      :class="tileClasses"
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
import RecordMeetingModal from '@/components/meeting/modals/RecordMeetingModal.vue';
import { useFeatureFlag } from '@/composables/use-feature-flag';
import { useImportMeeting } from '@/composables/use-import-meeting';
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
import { useModal } from 'vue-final-modal';

const tileClasses =
  'w-[95vw] h-[20vh] min-[440px]:h-[15vh] min-[1040px]:w-[30vw] min-[1040px]:h-[20vh]';

const isWebexEnabled = useFeatureFlag('webex');
const isImporting = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);

const router = useRouter();
const toaster = useToaster();
const { addMeetingMutation, startCaptureMutation } = useMeetings();
const { mutate: createMeeting } = addMeetingMutation();
const { mutateAsync: startCaptureAsync } = startCaptureMutation();
const { importFile } = useImportMeeting();

function openFilePicker() {
  if (isImporting.value) return;
  fileInput.value?.click();
}

async function onFileSelected(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;

  try {
    isImporting.value = true;
    await importFile(file);
  } finally {
    isImporting.value = false;
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
