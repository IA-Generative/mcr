<template>
  <DsfrInputGroup
    v-model="webconfUrl"
    class="m-0"
    :label="$t('meeting-v2.visio-form.webconf.url')"
    :hint="$t('meeting-v2.visio-form.webconf.url_hint')"
    :error-message="webconfUrlError"
    label-visible
  />
</template>

<script setup lang="ts">
import { t } from '@/plugins/i18n';
import { webconfUrlValidator } from '../meeting.schema';

const webconfUrl = ref<string>('');

const webconfUrlError = computed(() => {
  if (!webconfUrl.value) return '';
  if (!webconfUrlValidator.test(webconfUrl.value)) {
    return t('meeting-v2.visio-form.webconf.url_error');
  }
  return '';
});
</script>
