<template>
  <DsfrInputGroup
    v-model="visioUrl"
    class="m-0"
    :label="$t('meeting-v2.visio-form.visio.url')"
    :hint="$t('meeting-v2.visio-form.visio.url_hint')"
    :error-message="visoUrlError"
    label-visible
  />
</template>

<script setup lang="ts">
import { t } from '@/plugins/i18n';
import { visioUrlValidator } from '../meeting.schema';

const visioUrl = ref<string>('');

const visoUrlError = computed(() => {
  if (!visioUrl.value) return '';
  if (!visioUrlValidator.test(visioUrl.value)) {
    return t('meeting-v2.visio-form.visio.url_error');
  }
  return '';
});
</script>
