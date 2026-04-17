<template>
  <StatusTag :status="deliverableStatusToShow as DeliverableStatus" />
</template>

<script lang="ts">
import {
  getReportStatus,
  getTranscriptionStatus,
} from '@/services/deliverables/deliverables.service';
import {
  DeliverableStatus,
  type DeliverableFileType,
} from '@/services/deliverables/deliverables.types';
import type { MeetingStatus } from '@/services/meetings/meetings.types';
</script>
<script lang="ts" setup>
const props = defineProps<{
  deliverableType: DeliverableFileType;
  status: MeetingStatus;
}>();

const deliverableStatusToShow = computed(() => {
  switch (props.deliverableType) {
    case 'TRANSCRIPTION':
      return getTranscriptionStatus(props.status);
    case 'REPORT':
      return getReportStatus(props.status);
    default:
      return null;
  }
});
</script>
