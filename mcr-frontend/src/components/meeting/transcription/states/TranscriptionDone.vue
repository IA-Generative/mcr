<template>
  <div
    class="grid gap-10"
    :class="{
      'grid-cols-1 place-items-center': meetingStatus === 'REPORT_PENDING',
      'grid-cols-2 max-sm:grid-cols-1': meetingStatus !== 'REPORT_PENDING',
    }"
  >
    <DsfrButton
      no-outline
      class="h-fit self-center"
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
    <div v-if="isGetAudioMeetingEnabled">
      <div
        v-if="isLoadingAudio"
        class="flex items-center gap-2"
      >
        <VIcon
          name="ri-loader-3-line"
          animation="spin"
        />
        {{ $t('meeting.audio.loading') }}
      </div>
      <p
        v-else-if="audioError"
        class="text-red-500"
      >
        {{ $t('meeting.audio.error') }}
      </p>
      <audio
        v-else-if="audioSrc"
        controls
        :src="audioSrc"
      ></audio>
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

const props = defineProps<{
  meetingId: number;
  meetingName: string;
  meetingStatus: string;
}>();

const toaster = useToaster();
const { t } = useI18n();
const { downloadMutation, uploadMutation } = useMeetings();

const isGetAudioMeetingEnabled = useFeatureFlag('get_meeting_audio');

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

onMounted(async () => {
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
});

const file = ref<string>();
const isPending = computed(() => isDownloadPending.value || isUploadPending.value);

const handleFileChange = (files: FileList) => {
  if (!files.length) {
    return;
  }
  uploadTranscription({ file: files[0], id: props.meetingId });
};
</script>
