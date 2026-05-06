<template>
  <DsfrAlert
    v-if="showAlert"
    type="info"
    closeable
    data-testid="alert-availability"
    role="alertInfo"
    @close="closeAlert"
  >
    <p>
      {{ $t('meetings_v2.availability-alert-description.audio') }}
      <span style="font-weight: bold">
        {{ MAX_DELAY_TO_FETCH_AUDIO }}
        {{ $t('meetings_v2.availability-alert-description.days') }}
      </span>
    </p>
    <p>
      {{ $t('meetings_v2.availability-alert-description.pre-warning-pre-bold') }}
      <span style="font-weight: bold">
        {{ MAX_DELAY_TO_FETCH_DELIVERABLE }}
        {{ $t('meetings_v2.availability-alert-description.days') }}
      </span>
    </p>
  </DsfrAlert>
</template>

<script setup lang="ts">
import { useSessionAlert } from '@/composables/use-session-alert';
import { MAX_DELAY_TO_FETCH_AUDIO, MAX_DELAY_TO_FETCH_DELIVERABLE } from '@/config/meeting';

const { showAlert, closeAlert } = useSessionAlert('meeting-page-dsfr-alert-closed');
</script>
