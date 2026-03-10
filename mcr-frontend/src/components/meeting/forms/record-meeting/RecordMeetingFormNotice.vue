<template>
  <DsfrAlert
    :title="alertTitle"
    :type="isOnline ? 'info' : 'warning'"
    class="wrapper"
  >
    <template #default>
      <ul
        v-if="isOnline"
        class="mcr-li"
      >
        <i18n-t
          keypath="meeting.record-form.fields.notice.mic.text"
          tag="li"
        >
          <template #bold>
            <b>{{ $t('meeting.record-form.fields.notice.mic.bold') }}</b>
          </template>
        </i18n-t>
        <i18n-t
          keypath="meeting.record-form.fields.notice.noise.text"
          tag="li"
        >
          <template #bold>
            <b>{{ $t('meeting.record-form.fields.notice.noise.bold') }}</b>
          </template>
        </i18n-t>
        <i18n-t
          keypath="meeting.record-form.fields.notice.clarity.text"
          tag="li"
        >
          <template #bold>
            <b>{{ $t('meeting.record-form.fields.notice.clarity.bold') }}</b>
          </template>
        </i18n-t>
      </ul>
      <ul
        v-else
        class="mcr-li"
      >
        <li>{{ $t('meeting.transcription.recording.offline.keep-going') }}</li>
        <i18n-t
          keypath="meeting.transcription.recording.offline.reconnect.text"
          tag="li"
        >
          <template #bold>
            <b>{{ $t('meeting.transcription.recording.offline.reconnect.bold') }}</b>
          </template>
        </i18n-t>
      </ul>
    </template>
  </DsfrAlert>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';

const props = withDefaults(
  defineProps<{
    isOnline?: boolean;
  }>(),
  { isOnline: true },
);

const { t } = useI18n();

const alertTitle = computed(() =>
  props.isOnline
    ? t('meeting.record-form.fields.notice.title')
    : t('meeting.transcription.recording.offline.title'),
);
</script>

<style scoped>
ul.mcr-li li {
  --icon-size: 1.5rem;
  --dot-size: 1ex;
  --spacing: calc((var(--icon-size) - var(--dot-size)) * 0.5);
  list-style: disc;
  list-style-position: inside;
  padding-left: var(--spacing);
}

ul.mcr-li li::marker {
  margin-right: var(--spacing);
}

/* Because we display  */
.fr-alert--warning::before {
  mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'%3E%3Cpath d='m12.866 3 9.526 16.5a1 1 0 0 1-.866 1.5H2.474a1 1 0 0 1-.866-1.5L11.134 3a1 1 0 0 1 1.732 0ZM11 16v2h2v-2h-2Zm0-7v5h2V9h-2Z'/%3E%3C/svg%3E") !important;
}
</style>
