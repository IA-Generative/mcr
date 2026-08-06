<template>
  <DsfrTag
    :label="$t('meeting-v2.visio-recording.error.badge').toUpperCase()"
    class="rounded-sm bg-error-950 font-bold text-error-425"
    icon="fr-icon-error-fill"
  />
  <p>{{ $t('meeting-v2.visio-recording.error.description') }}</p>
  <DsfrButton
    :label="$t('meeting-v2.visio-recording.error.retry-button')"
    icon="fr-icon-refresh-line"
    :disabled="isRetryPending"
    @click="() => retryCapture(meetingId)"
  >
    <VIcon
      v-if="isRetryPending"
      name="ri-loader-3-line"
      animation="spin"
    />
  </DsfrButton>
</template>

<script setup lang="ts">
import { useMeetings } from '@/services/meetings/use-meeting';

const { meetingId } = defineProps<{
  meetingId: number;
}>();

const { startCaptureMutation } = useMeetings();
const { mutate: retryCapture, isPending: isRetryPending } = startCaptureMutation();
</script>
