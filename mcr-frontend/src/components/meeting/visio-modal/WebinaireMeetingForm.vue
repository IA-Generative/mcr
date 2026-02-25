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
</template>

<script setup lang="ts">
import { t } from '@/plugins/i18n';
import { webinaireModeratorUrlValidator } from '../meeting.schema';

const webinaireUrl = ref<string>('');

const webinaireUrlError = computed(() => {
  if (!webinaireUrl.value) return '';
  if (!webinaireModeratorUrlValidator.test(webinaireUrl.value)) {
    return t('meeting-v2.visio-form.webinaire.url_error');
  }
  return '';
});
</script>
