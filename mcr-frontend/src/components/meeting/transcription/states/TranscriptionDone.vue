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
  </div>
</template>

<script setup lang="ts">
import { useMeetings } from '@/services/meetings/use-meeting';
import useToaster from '@/composables/use-toaster';
import { downloadFileFromAxios } from '@/utils/file';
import { useI18n } from 'vue-i18n';
import { sanitizeFilename } from '@/utils/formatters';

const props = defineProps<{
  meetingId: number;
  meetingName: string;
  meetingStatus: string;
}>();

const toaster = useToaster();
const { t } = useI18n();
const { downloadMutation, uploadMutation } = useMeetings();

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
    console.log(err);
    toaster.addErrorMessage(t('error.default'));
  },
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
