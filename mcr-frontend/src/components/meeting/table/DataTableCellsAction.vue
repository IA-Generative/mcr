<template>
  <component
    :is="currentComponent"
    v-if="currentComponent"
    :cell="cell"
  />
  <template v-else>{{ cell }}</template>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import DataCellMeeting from './cells/DataCellMeeting.vue';
import DataCellAction from './cells/DataCellAction.vue';

const props = defineProps<{
  colKey: string;
  cell: unknown;
}>();

const currentComponent = computed(() => {
  switch (props.colKey) {
    case 'title':
      return DataCellMeeting;
    case 'actions':
      return DataCellAction;
    default:
      return null;
  }
});
</script>
