<template>
  <div
    v-if="!hasWaitingTimeReachedDeadline"
    class="fr-alert fr-alert--info fr-alert--sm pr-2"
  >
    <p>
      {{ props.message }}
      <span class="font-bold">
        {{ formatRoundedDurationMinutes(waitingTimeMinutes) }}
      </span>
    </p>
  </div>
  <div
    v-else
    class="fr-alert fr-alert--warning fr-alert--sm pr-2"
  >
    <p>
      <span class="font-bold">
        {{ $t('meeting.transcription.wait-time.reached-deadline') }}
      </span>
    </p>
  </div>
</template>

<script setup lang="ts">
import { formatRoundedDurationMinutes } from '@/utils/timeFormatting';

const props = defineProps<{
  waitingTimeMinutes?: number;
  message: string;
}>();

const hasWaitingTimeReachedDeadline = computed(() => {
  return props.waitingTimeMinutes !== undefined && props.waitingTimeMinutes <= 0;
});
</script>
