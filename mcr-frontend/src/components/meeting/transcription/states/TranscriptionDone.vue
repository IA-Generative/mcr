<template>
  <div
    class="grid gap-10"
    :class="{
      'grid-cols-1 place-items-center': meetingStatus === 'REPORT_PENDING',
      'grid-cols-2 max-sm:grid-cols-1': meetingStatus !== 'REPORT_PENDING',
    }"
  >
    <div class="flex flex-col gap-10 items-center relative">
      <div
        v-if="transcriptionDriveUrl"
        class="flex flex-col gap-2 items-center"
      >
        <a
          :href="transcriptionDriveUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="fr-btn fr-btn--icon-right fr-icon-external-link-line"
        >
          {{ $t('meeting.transcription.open-on-drive') }}
        </a>
        <a
          href="#"
          class="fr-link fr-link--sm"
          @click.prevent="downloadTranscription(meetingId)"
        >
          {{ $t('meeting.transcription.download') }}
          <VIcon
            v-if="isPending"
            name="ri-loader-3-line"
            animation="spin"
            scale="0.8"
          />
        </a>
      </div>

      <DsfrButton
        v-else
        no-outline
        class="h-fit"
        icon="fr-icon-download-fill"
        @click="() => downloadTranscription(meetingId)"
      >
        {{ $t('meeting.transcription.download') }}
        <VIcon
          v-if="isPending"
          name="ri-loader-3-line"
          animation="spin"
        />
      </DsfrButton>

      <DsfrButton
        v-if="isGetAudioMeetingEnabled && !isMeetingAudioRequired && isMeetingRecent"
        class="h-fit self-center"
        secondary
        @click="handleRequireMeetingAudio()"
      >
        {{ $t('meeting-v2.audio-player.button') }}
      </DsfrButton>
      <div
        v-if="isGetAudioMeetingEnabled && isMeetingAudioRequired && isMeetingRecent"
        class="flex items-center justify-center w-full"
        :class="{ 'absolute top-full left-0 -mt-8': audioError }"
      >
        <VIcon
          v-if="isLoadingAudio"
          class="justify-self-auto"
          name="ri-loader-3-line"
          animation="spin"
        />
        <DsfrNotice
          v-else-if="audioError"
          class="bottom-2"
          :title="$t('meeting-v2.audio-player.error')"
          type="alert"
        />
        <audio
          v-else-if="audioSrc"
          controls
          controlslist="nodownload"
          :src="audioSrc"
        ></audio>
      </div>
    </div>

    <div
      v-if="meetingStatus !== 'REPORT_PENDING'"
      class="flex flex-col"
    >
      <DsfrFileUpload
        v-model="file"
        :label="$t('meeting.transcription.upload')"
        :hint="$t('meeting.transcription.format-accepted')"
        :accept="['.docx']"
        @change="handleFileChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useMeetings } from '@/services/meetings/use-meeting';
import useToaster from '@/composables/use-toaster';
import { downloadFileFromAxios } from '@/utils/file';
import { useI18n } from 'vue-i18n';
import { sanitizeFilename } from '@/utils/formatters';
import { isAxiosError } from 'axios';
import HttpService, { API_PATHS } from '@/services/http/http.service';
import { useFeatureFlag } from '@/composables/use-feature-flag';
import { parseISO, differenceInDays } from 'date-fns';
import type { DeliverableDto } from '@/services/meetings/meetings.types';
import { MAX_DELAY_TO_FETCH_AUDIO } from '@/config/meeting';

const props = withDefaults(
  defineProps<{
    meetingId: number;
    meetingName: string;
    meetingStatus: string;
    creationDate: string;
    deliverables?: DeliverableDto[];
  }>(),
  { deliverables: () => [] },
);

const transcriptionDriveUrl = computed(() => {
  const deliverable = props.deliverables.find(
    (d) => d.file_type === 'TRANSCRIPTION' && d.external_url,
  );
  return deliverable?.external_url ?? null;
});

const toaster = useToaster();
const { t } = useI18n();
const { downloadMutation, uploadMutation } = useMeetings();

const isGetAudioMeetingEnabled = useFeatureFlag('get_meeting_audio');
const isMeetingRecent = computed(
  () => differenceInDays(new Date(), parseISO(props.creationDate)) <= MAX_DELAY_TO_FETCH_AUDIO,
);
const audioStorageKey = `mcr-audio-required-${props.meetingId}`;
const isMeetingAudioRequired = ref(localStorage.getItem(audioStorageKey) === 'true');

function handleRequireMeetingAudio(): void {
  isMeetingAudioRequired.value = true;
  localStorage.setItem(audioStorageKey, 'true');
}

const { mutate: downloadTranscription, isPending: isDownloadPending } = downloadMutation({
  onSuccess: (response) => {
    const filename = `Transcription_${props.meetingName}`;
    downloadFileFromAxios(response, sanitizeFilename(filename));
  },
  onError: (err) => {
    console.log(err);
    toaster.addErrorMessage(t('error.default'));
  },
});

const { mutate: uploadTranscription, isPending: isUploadPending } = uploadMutation({
  onSuccess: () => {
    file.value = undefined;
    toaster.addSuccessMessage(t('meeting.transcription.upload-success'));
  },
  onError: (err) => {
    if (isAxiosError(err) && err.response?.status === 415) {
      toaster.addErrorMessage(t('meeting.transcription.upload-invalid-format'));
    } else {
      toaster.addErrorMessage(t('error.default'));
    }
  },
});

const audioSrc = ref<string>();
const isLoadingAudio = ref(true);
const audioError = ref(false);

watch(
  isMeetingAudioRequired,
  async (isRequired) => {
    if (!isRequired) return;
    try {
      const response = await HttpService.get(`${API_PATHS.MEETINGS}/${props.meetingId}/audio`, {
        responseType: 'blob',
      });
      audioSrc.value = URL.createObjectURL(response.data);
    } catch (err) {
      console.error('Failed to fetch audio', err);
      audioError.value = true;
    } finally {
      isLoadingAudio.value = false;
    }
  },
  { immediate: true },
);

const file = ref<string>();
const isPending = computed(() => isDownloadPending.value || isUploadPending.value);

const handleFileChange = (files: FileList) => {
  if (!files.length) {
    return;
  }
  uploadTranscription({ file: files[0], id: props.meetingId });
};
</script>
