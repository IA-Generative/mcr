<template>
  <div
    v-if="!hasWaitingTimeReachedDeadline"
    class="fr-alert fr-alert--info fr-alert--sm pr-2"
  >
    <p>
      {{ $t('meeting.transcription.wait-time.estimation') }}
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
  waitingTimeMinutes: number | undefined;
}>();

const hasWaitingTimeReachedDeadline = computed(() => {
  return props.waitingTimeMinutes && props.waitingTimeMinutes <= 0;
});
</script>
