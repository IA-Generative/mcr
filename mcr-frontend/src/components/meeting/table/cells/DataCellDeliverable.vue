<template>
  <StatusTag :status="deliverableStatusToShow as DeliverableStatus" />
</template>

<script lang="ts">
import { reportTag, transcriptionTag } from '@/services/deliverables/deliverables.service';
import {
  DeliverableStatus,
  type DeliverableFileType,
} from '@/services/deliverables/deliverables.types';
import type { DeliverableDto } from '@/services/meetings/meetings.types';
</script>
<script lang="ts" setup>
const props = defineProps<{
  deliverableType: DeliverableFileType;
  deliverables: DeliverableDto[];
}>();

const deliverableStatusToShow = computed(() => {
  switch (props.deliverableType) {
    case 'TRANSCRIPTION':
      return transcriptionTag(props.deliverables);
    case 'REPORT':
      return reportTag(props.deliverables);
    default:
      return null;
  }
});
</script>
