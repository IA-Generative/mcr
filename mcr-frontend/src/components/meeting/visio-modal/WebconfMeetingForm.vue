<template>
  <DsfrInputGroup
    v-model="webconfUrl"
    class="m-0"
    :label="$t('meeting-v2.visio-form.webconf.url')"
    :hint="$t('meeting-v2.visio-form.webconf.url_hint')"
    :error-message="webconfUrlError"
    label-visible
  />

  <hr />

  <div class="flex justify-end">
    <DsfrButton
      :label="$t('meeting-v2.visio-form.submit')"
      icon="fr-icon-play-circle-fill"
      :disabled="!isSubmitEnabled"
      @click="handleSubmit()"
    />
  </div>
</template>

<script setup lang="ts">
import { t } from '@/plugins/i18n';
import { webconfUrlValidator } from '../meeting.schema';
import type { AddOnlineMeetingDto } from '@/services/meetings/meetings.types';

const props = defineProps<{
  title: string;
}>();
const webconfUrl = ref<string>('');

const webconfUrlError = computed(() => {
  if (!webconfUrl.value) return '';
  if (!webconfUrlValidator.test(webconfUrl.value)) {
    return t('meeting-v2.visio-form.webconf.url_error');
  }
  return '';
});

const isSubmitEnabled = computed(() => {
  return props.title !== '' && webconfUrlValidator.test(webconfUrl.value);
});

const emit = defineEmits<{
  submit: [form: AddOnlineMeetingDto];
  cancel: [];
}>();

function handleSubmit() {
  const dto: AddOnlineMeetingDto = {
    name: props.title,
    url: webconfUrl.value,
    name_platform: 'WEBCONF',
    meeting_password: null,
    meeting_platform_id: null,
    creation_date: new Date().toISOString(),
  };
  emit('submit', dto);
}
</script>
