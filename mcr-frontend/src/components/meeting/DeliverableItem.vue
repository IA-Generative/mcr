<template>
  <div class="deliverable-item">
    <StatusTag :status="status" />

    <p class="deliverable-item__title">{{ title }}</p>

    <div class="deliverable-item__footer">
      <span class="deliverable-item__file-info">
        {{ fileFormat }}
        <template v-if="fileSize"> - {{ fileSize }}</template>
      </span>
      <button class="deliverable-item__download fr-icon-download-fill" />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DeliverableStatus } from '@/services/deliverables/deliverables.types';

defineProps<{
  title: string;
  status: DeliverableStatus;
  fileFormat: string;
  fileSize?: string;
}>();
</script>

<style scoped>
.deliverable-item {
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  border-bottom: 3px solid var(--blue-france-sun-113-625);
  background-color: var(--grey-1000-50);
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

.deliverable-item__download {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-default-grey);
  font-size: 1rem;
  padding: 0;
}
</style>
