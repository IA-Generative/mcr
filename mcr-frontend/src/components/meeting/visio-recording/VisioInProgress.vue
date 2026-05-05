<template>
  <DsfrTag
    :label="$t('meeting-v2.visio-recording.in-progress.badge').toUpperCase()"
    class="bg-success-950 text-success-425 rounded font-bold"
    icon="fr-icon-circle-fill"
  />
  <h2
    v-if="showTimer"
    class="font-bold text-2xl/8"
  >
    {{ leftPad(time.hours.value) }}:{{ leftPad(time.minutes.value) }}:{{
      leftPad(time.seconds.value)
    }}
  </h2>
</template>

<script setup lang="ts">
import { useStopwatch } from 'vue-timer-hook';

const props = defineProps<{
  startDate?: string;
}>();

const showTimer = computed(() => !!props.startDate);
const offsetSeconds = computed(() => {
  if (!props.startDate) return 0;
  return Math.floor((Date.now() - new Date(props.startDate).getTime()) / 1000);
});
const time = useStopwatch(offsetSeconds.value, showTimer.value);

function leftPad(value: number): string {
  return value.toString().padStart(2, '0');
}
</script>
