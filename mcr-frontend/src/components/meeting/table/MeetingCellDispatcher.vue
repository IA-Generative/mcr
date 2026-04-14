<template>
  <DataCellMeetingTitle
    v-if="colKey === 'title'"
    :cell="cell as MeetingTitleCell"
  />
  <DataCellAction
    v-else-if="colKey === 'actions'"
    :cell="cell as MeetingDto"
  />
  <template v-else>{{ cell }}</template>
</template>

<script setup lang="ts">
import type { ColKey, CellMap, MeetingTitleCell } from './types';
import type { MeetingDto } from '@/services/meetings/meetings.types';
import DataCellMeetingTitle from './cells/DataCellMeetingTitle.vue';
import DataCellAction from './cells/DataCellAction.vue';

defineProps<{
  colKey: string;
  cell: CellMap[ColKey];
}>();
</script>
