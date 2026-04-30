<template>
  <button
    class="deliverable-item"
    :disabled="status !== 'AVAILABLE'"
    @click="emit('download', deliverableId)"
  >
    <StatusTag :status="status" />

    <p class="deliverable-item__title">{{ title }}</p>

    <div class="deliverable-item__footer">
      <span class="deliverable-item__file-info">
        {{ fileFormat }}
        <template v-if="fileSize"> - {{ fileSize }}</template>
      </span>
      <span class="deliverable-item__download-icon fr-icon-download-line" />
    </div>
  </button>
</template>

<script setup lang="ts">
import type { DeliverableStatus } from '@/services/deliverables/deliverables.types';

defineProps<{
  deliverableId: number;
  title: string;
  status: DeliverableStatus;
  fileFormat: string;
  fileSize?: string;
}>();

const emit = defineEmits<{ download: [id: number] }>();
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

.deliverable-item__title {
  color: var(--blue-france-sun-113-625);
  font-weight: bold;
  font-size: 0.875rem;
  margin: 0;
}

.deliverable-item__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.deliverable-item__file-info {
  color: var(--text-default-grey);
  font-size: 0.75rem;
}

.deliverable-item__download-icon {
  color: var(--blue-france-sun-113-625);
  font-size: 1rem;
}
</style>
