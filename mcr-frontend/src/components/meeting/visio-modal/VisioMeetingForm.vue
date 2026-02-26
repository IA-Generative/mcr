<template>
  <DsfrInputGroup
    v-model="visioUrl"
    class="m-0"
    :label="$t('meeting-v2.visio-form.visio.url')"
    :hint="$t('meeting-v2.visio-form.visio.url_hint')"
    :error-message="visoUrlError"
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
import { visioUrlValidator } from '../meeting.schema';
import type { AddOnlineMeetingDto } from '@/services/meetings/meetings.types';

const props = defineProps<{
  title: string;
}>();

const visioUrl = ref<string>('');

const visoUrlError = computed(() => {
  if (!visioUrl.value) return '';
  if (!visioUrlValidator.test(visioUrl.value)) {
    return t('meeting-v2.visio-form.visio.url_error');
  }
  return '';
});

const isSubmitEnabled = computed(() => {
  return props.title !== '' && visioUrlValidator.test(visioUrl.value);
});

const emit = defineEmits<{
  submit: [visioUrl: AddOnlineMeetingDto];
  cancel: [];
}>();

function handleSubmit() {
  const dto: AddOnlineMeetingDto = {
    name: props.title,
    name_platform: 'VISIO',
    url: visioUrl.value,
    meeting_password: null,
    meeting_platform_id: null,
    creation_date: new Date().toISOString(),
  };
  emit('submit', dto);
}
</script>
