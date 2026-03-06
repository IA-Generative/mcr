<template>
  <DsfrInputGroup
    v-model="comuUrl"
    class="m-0"
    :label="$t('meeting-v2.visio-form.comu.url')"
    :hint="$t('meeting-v2.visio-form.comu.url_hint')"
    :error-message="comuUrlError"
    label-visible
    :disabled="!isUrlEnabled"
  />

  <VisioConnectionSeparator />

  <div class="flex flex-row gap-x-6 pb-4">
    <DsfrInputGroup
      v-model="comuId"
      class="w-full flex-1"
      :label="$t('meeting-v2.visio-form.comu.meeting_id')"
      :error-message="comuIdError"
      label-visible
      :disabled="!isIdPasswordEnabled"
    />

    <DsfrInputGroup
      v-model="comuPassword"
      class="w-full flex-1"
      :label="$t('meeting-v2.visio-form.comu.access_code')"
      :error-message="comuPasswordError"
      label-visible
      :disabled="!isIdPasswordEnabled"
    />
  </div>
</template>

<script setup lang="ts">
import { useField } from 'vee-validate';
import VisioConnectionSeparator from './VisioConnectionSeparator.vue';

const { value: comuUrl, errorMessage: comuUrlError } = useField<string>('url');
const { value: comuPassword, errorMessage: comuPasswordError } =
  useField<string>('meeting_password');
const { value: comuId, errorMessage: comuIdError } = useField<string>('meeting_platform_id');

const isIdPasswordEnabled = computed(() => {
  return comuUrl.value === null || comuUrl.value === '';
});
const isUrlEnabled = computed(() => {
  return (
    (comuPassword.value === null || comuPassword.value === '') &&
    (comuId.value === null || comuId.value === '')
  );
});
</script>

<style scoped>
:deep(.fr-input-group) {
  flex-grow: 1;
  min-width: 50%;
}

:deep(.fr-label) {
  color: unset;
}

:deep(.fr-hint-text) {
  color: var(--text-mention-grey);
}
</style>
