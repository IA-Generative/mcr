<template>
  <DsfrInputGroup
    v-model="visioUrl"
    class="m-0"
    :label="$t('meeting-v2.visio-form.visio.url')"
    :hint="$t('meeting-v2.visio-form.visio.url_hint')"
    :error-message="visioUrlError"
    label-visible
  />
</template>

<script setup lang="ts">
import { useField } from 'vee-validate';

const { value: visioUrl, errorMessage: visioUrlError } = useField<string>('url');
</script>
