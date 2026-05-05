<template>
  <VisioConnecting v-if="cardState === 'connecting'" />

  <VisioInProgress
    v-else-if="cardState === 'in-progress'"
    :start-date="startDate"
  />

  <VisioError
    v-else-if="cardState === 'error'"
    :meeting-id="meetingId"
  />
</template>

<script setup lang="ts">
import VisioConnecting from '@/components/meeting/visio-recording/VisioConnecting.vue';
import VisioInProgress from '@/components/meeting/visio-recording/VisioInProgress.vue';
import VisioError from '@/components/meeting/visio-recording/VisioError.vue';
import type { MeetingStatus } from '@/services/meetings/meetings.types';

const props = defineProps<{
  meetingId: number;
  status: MeetingStatus;
  startDate?: string;
}>();

type VisioRecordingState = 'connecting' | 'in-progress' | 'error';

const cardState = computed<VisioRecordingState | null>(() => {
  if (props.status === 'CAPTURE_PENDING' || props.status === 'CAPTURE_BOT_IS_CONNECTING')
    return 'connecting';
  if (props.status === 'CAPTURE_IN_PROGRESS') return 'in-progress';
  if (props.status === 'CAPTURE_FAILED' || props.status === 'CAPTURE_BOT_CONNECTION_FAILED')
    return 'error';
  return null;
});
</script>
