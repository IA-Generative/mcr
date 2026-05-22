<template>
  <HoverTooltip
    v-if="isPendingOrInProgress"
    :content="$t('meeting-v2.deliverable-card.tooltip.in-progress')"
    class="deliverable-item-host"
  >
    <button
      class="deliverable-item deliverable-item--inactive"
      :aria-disabled="true"
      @click="onClick"
    >
      <StatusTag :status="status" />

      <p class="text-blue-france-sun font-bold text-sm m-0">{{ title }}</p>

      <div class="flex items-center justify-between">
        <span class="text-[var(--text-default-grey)] text-xs">
          {{ fileFormat }}
          <template v-if="fileSize"> - {{ fileSize }}</template>
        </span>
        <span class="text-blue-france-sun text-base fr-icon-download-line" />
      </div>
    </button>
  </HoverTooltip>
  <button
    v-else
    class="deliverable-item"
    :disabled="status !== 'AVAILABLE'"
    @click="onClick"
  >
    <StatusTag :status="status" />

    <p class="text-blue-france-sun font-bold text-sm m-0">{{ title }}</p>

    <div class="flex items-center justify-between">
      <span class="text-[var(--text-default-grey)] text-xs">
        {{ fileFormat }}
        <template v-if="fileSize"> - {{ fileSize }}</template>
      </span>
      <span class="text-blue-france-sun text-base fr-icon-download-line" />
    </div>
  </button>
</template>

<script setup lang="ts">
import HoverTooltip from '@/components/core/HoverTooltip.vue';
import type { DeliverableStatus } from '@/services/deliverables/deliverables.types';

const props = defineProps<{
  deliverableId: number;
  title: string;
  status: DeliverableStatus;
  fileFormat: string;
  fileSize?: string;
}>();

const emit = defineEmits<{ download: [id: number] }>();

const isPendingOrInProgress = computed(
  () => props.status === 'PENDING' || props.status === 'IN_PROGRESS',
);

function onClick(): void {
  if (props.status !== 'AVAILABLE') return;
  emit('download', props.deliverableId);
}
</script>

<style scoped>
.deliverable-item {
  appearance: none;
  font: inherit;
  text-align: left;
  border: 1px solid #dddddd;
  border-bottom: 3px solid var(--blue-france-sun-113-625);
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  background-color: var(--grey-1000-50);
  width: calc(50% - 0.25rem);
  cursor: pointer;
}

.deliverable-item:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.deliverable-item--inactive {
  opacity: 0.5;
  cursor: default;
}

.deliverable-item-host {
  width: calc(50% - 0.25rem);
}

.deliverable-item-host .deliverable-item {
  width: 100%;
}
</style>
