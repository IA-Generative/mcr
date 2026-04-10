<template>
  <DsfrInputGroup
    v-model="webexUrl"
    class="m-0"
    :label="$t('meeting-v2.visio-form.webex.url')"
    :hint="$t('meeting-v2.visio-form.webex.url_hint')"
    :error-message="webexUrlError"
    label-visible
  />
</template>

<script setup lang="ts">
import { useField } from 'vee-validate';

const { value: webexUrl, errorMessage: webexUrlError } = useField<string>('url');
</script>
