<template>
  <DsfrInputGroup
    v-model="webinaireUrl"
    class="m-0"
    :label="$t('meeting-v2.visio-form.webinaire.url')"
    :hint="$t('meeting-v2.visio-form.webinaire.url_hint')"
    :error-message="webinaireUrlError"
    label-visible
  />
</template>

<script setup lang="ts">
import { useField } from 'vee-validate';

const { value: webinaireUrl, errorMessage: webinaireUrlError } = useField<string>('url');
</script>
