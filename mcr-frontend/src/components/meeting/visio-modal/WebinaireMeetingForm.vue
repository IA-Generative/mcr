<template>
  <DsfrInputGroup
    v-model="webinaireUrl"
    class="m-0"
    :label="$t('meeting-v2.visio-form.webinaire.url')"
    :hint="$t('meeting-v2.visio-form.webinaire.url_hint')"
    :error-message="webinaireUrlError"
    label-visible
  />

  <VisioConnectionSeparator />

  <DsfrInputGroup
    class="m-0"
    :label="$t('meeting-v2.visio-form.webinaire.connection_code')"
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
import { webinaireModeratorUrlValidator } from '../meeting.schema';
import type { AddOnlineMeetingDto } from '@/services/meetings/meetings.types';

const props = defineProps<{
  title: string;
}>();

const webinaireConnectionCode = ref<string>('');

const webinaireUrl = ref<string>('');
const webinaireUrlError = computed(() => {
  if (!webinaireUrl.value) return '';
  if (!webinaireModeratorUrlValidator.test(webinaireUrl.value)) {
    return t('meeting-v2.visio-form.webinaire.url_error');
  }
  return '';
});

const isSubmitEnabled = computed(() => {
  return props.title !== '' && webinaireModeratorUrlValidator.test(webinaireUrl.value);
});

const emit = defineEmits<{
  submit: [visioUrl: AddOnlineMeetingDto];
  cancel: [];
}>();

function handleSubmit() {
  const dto: AddOnlineMeetingDto = {
    name: props.title,
    name_platform: 'WEBINAIRE',
    url: webinaireUrl.value ?? undefined,
    meeting_password: null,
    meeting_platform_id: null,
    creation_date: new Date().toISOString(),
  };
  emit('submit', dto);
}
</script>
