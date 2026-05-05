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
  <DsfrButton
    :label="$t('meeting-v2.visio-recording.in-progress.stop-button')"
    icon="fr-icon-stop-circle-fill"
    @click="openEndModal"
  />
</template>

<script setup lang="ts">
import { useStopwatch } from 'vue-timer-hook';
import { useModal } from 'vue-final-modal';
import EndLiveMeetingModal from '@/components/meeting/modals/EndLiveMeetingModal.vue';
import { leftPad } from '@/services/meetings/meetings-datetime';
import { useMeetings } from '@/services/meetings/use-meeting';

const props = defineProps<{
  meetingId: number;
  startDate?: string;
}>();

const { stopCaptureMutation } = useMeetings();
const { mutate: stopCapture } = stopCaptureMutation();

const { open: openEndModal } = useModal({
  component: EndLiveMeetingModal,
  attrs: {
    onSuccess: () => stopCapture(props.meetingId),
  },
});

const showTimer = computed(() => !!props.startDate);
const offsetSeconds = computed(() => {
  if (!props.startDate) return 0;
  return Math.floor((Date.now() - new Date(props.startDate).getTime()) / 1000);
});
const time = useStopwatch(offsetSeconds.value, showTimer.value);
</script>
