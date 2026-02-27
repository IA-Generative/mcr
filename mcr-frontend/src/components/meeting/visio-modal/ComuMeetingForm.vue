<template>
  <DsfrInputGroup
    v-model="comuUrl"
    class="m-0"
    :label="$t('meeting-v2.visio-form.comu.url')"
    :hint="$t('meeting-v2.visio-form.comu.url_hint')"
    :error-message="comuUrlError"
    label-visible
  />

  <VisioConnectionSeparator />

  <div class="flex flex-row gap-x-6 pb-4">
    <DsfrInputGroup
      class="w-full flex-1"
      :label="$t('meeting-v2.visio-form.comu.access_code')"
      label-visible
    />

    <DsfrInputGroup
      v-model="comuId"
      class="w-full flex-1"
      :label="$t('meeting-v2.visio-form.comu.meeting_id')"
      :error-message="comuIdError"
      label-visible
    />
  </div>
</template>

<script setup lang="ts">
import { t } from '@/plugins/i18n';
import { comuPrivateUrlValidator } from '../meeting.schema';
import VisioConnectionSeparator from './VisioConnectionSeparator.vue';

const comuUrl = ref<string>('');
const comuUrlError = computed(() => {
  if (!comuUrl.value) return '';
  if (!comuPrivateUrlValidator.test(comuUrl.value)) {
    return t('meeting-v2.visio-form.comu.url_error');
  }
  return '';
});

const comuId = ref<string>('');
const comuIdError = computed(() => {
  if (!comuId.value) return '';
  if (!RegExp(/^[0-9]+$/).test(comuId.value)) {
    return t('meeting-v2.visio-form.comu.meeting_id_error');
  }
  return '';
});
</script>

<style scoped>
:deep(.fr-input-group) {
  flex-grow: 1;
  min-width: 50%;
}
</style>
