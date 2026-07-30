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
import { useField } from 'vee-validate';

const { value: webconfUrl, errorMessage: webconfUrlError } = useField<string>('url');
</script>
