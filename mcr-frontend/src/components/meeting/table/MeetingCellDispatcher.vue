<template>
  <DataCellMeetingTitle
    v-if="colKey === 'title'"
    :cell="cell as MeetingTitleCell"
  />
  <DataCellDeliverable
    v-else-if="colKey === 'transcription' || colKey === 'report'"
    :cell="cell as MeetingStatus"
    :deliverable-type="colKey.toUpperCase() as DeliverableFileType"
  />
  <DataCellAction
    v-else-if="colKey === 'actions'"
    :cell="cell as MeetingDto"
  />

  <template v-else>{{ cell }}</template>
</template>

<script setup lang="ts">
import type { ColKey, CellMap, MeetingTitleCell } from './types';
import type { MeetingDto, MeetingStatus } from '@/services/meetings/meetings.types';
import DataCellMeetingTitle from './cells/DataCellMeetingTitle.vue';
import DataCellAction from './cells/DataCellAction.vue';
import type { DeliverableFileType } from '@/services/deliverables/deliverables.types';

defineProps<{
  colKey: string;
  cell: CellMap[ColKey];
}>();
</script>
