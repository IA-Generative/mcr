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
      v-model="comuPassword"
      class="w-full flex-1"
      :label="$t('meeting-v2.visio-form.comu.access_code')"
      :error-message="comuPasswordError"
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
import { useField } from 'vee-validate';

const { value: comuUrl, errorMessage: comuUrlError } = useField<string>('url');
const { value: comuPassword, errorMessage: comuPasswordError } =
  useField<string>('meeting_password');
const { value: comuId, errorMessage: comuIdError } = useField<string>('meeting_platform_id');
</script>

<style scoped>
:deep(.fr-input-group) {
  flex-grow: 1;
  min-width: 50%;
}
</style>
