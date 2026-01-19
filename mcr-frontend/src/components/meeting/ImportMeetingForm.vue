<template>
  <form @submit.prevent="onSubmit">
    <div class="grid grid-cols-1 gap-4">
      <ImportMeetingProgressBar
        v-if="transcodingStatus.isTranscoding"
        :progress="transcodingStatus.progress"
        @on-cancel="handleCancelVideoUpload"
      />

      <DsfrFileUpload
        v-if="shouldDisplayUploadFile()"
        v-model="filePath"
        v-bind="fileAttrs"
        :label="$t('meeting.import-form.fields.file.label')"
        :hint="
          $t(
            isMultipartUploadEnabled()
              ? 'meeting.import-form.fields.file.hint-with-multipart-upload-enabled'
              : 'meeting.import-form.fields.file.hint',
          )
        "
        accept="video/*, audio/*"
        @change="(fileList) => handleFileChange(fileList)"
      />
      <DsfrInputGroup
        v-model="name"
        required
        :error-message="errors.name"
        :label="$t('meeting.import-form.fields.name')"
        label-visible
        aria-required="true"
        v-bind="nameAttrs"
        wrapper-class="w-full"
        class="w-full"
      />
    </div>

    <div class="mt-8 text-center">
      <slot
        name="actions"
        :disabled="isDisabled"
      >
        <DsfrButtonGroup
          inline-layout-when="md"
          align="right"
          reverse
        >
          <DsfrButton
            :disabled="isDisabled"
            type="submit"
            icon="ri-file-add-line"
          >
            <VIcon
              v-if="isPending"
              name="ri-loader-4-line"
              animation="spin"
            />
            {{ $t('meeting.import-form.submit') }}
          </DsfrButton>
          <DsfrButton
            tertiary
            no-outline
            type="button"
            @click="emit('cancel')"
            >{{ $t('common.cancel') }}</DsfrButton
          >
        </DsfrButtonGroup>
      </slot>
    </div>
  </form>
</template>

<script setup lang="ts">
import { useForm, useIsFormDirty, useIsFormValid } from 'vee-validate';
import { toTypedSchema } from '@vee-validate/yup';
import {
  importMeetingFieldsToMeetingDtoAndFile,
  ImportMeetingSchema,
  isMultipartUploadEnabled,
} from '@/components/meeting/forms/import-meeting/import-meeting.schema';
import type { AddImportMeetingDtoAndFile } from '@/services/meetings/meetings.types';
import { useVideo2audioConverter } from '@/utils/video2audioConverter';
import { t } from '@/plugins/i18n';

const props = defineProps<{
  isPending: boolean;
  meetingName?: string;
}>();

const emit = defineEmits<{
  submit: [values: AddImportMeetingDtoAndFile];
  cancel: [];
}>();

const { defineField, setFieldValue, setFieldTouched, setFieldError, errors, handleSubmit } =
  useForm({
    initialValues: {
      name: props.meetingName,
    },
    validationSchema: toTypedSchema(ImportMeetingSchema),
  });

const isDirty = useIsFormDirty();
const isValid = useIsFormValid();

const isDisabled = computed(() => {
  return props.isPending || !isDirty.value || !isValid.value;
});

const onSubmit = handleSubmit((values) => {
  const dtoAndFile = importMeetingFieldsToMeetingDtoAndFile(values);
  emit('submit', dtoAndFile);
});

// This is not used in the form but is needed to display the name of the file when selected
// file is the File object that is used to send to the backend
const filePath = ref('');
const [name, nameAttrs] = defineField('name');
// ref to the file being uploaded, it is set via setValues in handleFileChange. The ts error is because this isn't detected
const [, fileAttrs] = defineField('file', {
  props: (state) => {
    return {
      error: state.touched && state.errors ? state.errors[0] : undefined,
    };
  },
});
const transcodingStatus = reactive({
  progress: 0,
  isTranscoding: false,
});

const handleFileChange = (files: FileList) => {
  setFieldTouched('file', false);

  if (files.length == 0) {
    return;
  }

  if (files[0].type.startsWith('video/')) {
    handleVideoUpload(files[0]);
  } else {
    setFormAudioFile(files[0]);
  }
};

const { transcodeToMp3, stopTranscoding } = useVideo2audioConverter((progress: number) => {
  transcodingStatus.progress = numberToPercent(progress);
});

async function handleVideoUpload(videoFile: File) {
  try {
    transcodingStatus.isTranscoding = true;
    const mp3ConvertedFile = await transcodeToMp3(videoFile);
    setFormAudioFile(mp3ConvertedFile);
  } catch (error) {
    setFieldTouched('file', true);
    setFieldError('file', t('meeting.import-form.errors.file-invalid'));
  }
}

function setFormAudioFile(audioFile: File) {
  setFieldValue('file', audioFile);
  setFieldTouched('file', true);
}

function numberToPercent(value: number): number {
  return Math.round(value * 100);
}

function handleCancelVideoUpload() {
  stopTranscoding();
  filePath.value = '';
  transcodingStatus.isTranscoding = false;
  transcodingStatus.progress = 0;
}

function shouldDisplayUploadFile() {
  return !transcodingStatus.isTranscoding;
}
</script>
