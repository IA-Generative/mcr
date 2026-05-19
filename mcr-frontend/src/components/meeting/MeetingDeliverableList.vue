<template>
  <div
    v-if="displayedDeliverables.length"
    class="flex gap-2 flex-wrap"
  >
    <DeliverableItem
      v-for="item in displayedDeliverables"
      :key="item.id"
      :deliverable-id="item.id"
      :title="item.title"
      :status="item.status"
      :file-format="item.fileFormat"
      :file-size="item.fileSize"
      :external-url="item.externalUrl"
      @download="$emit('downloadDeliverable', $event)"
    />
  </div>
</template>

<script setup lang="ts">
import DeliverableItem from './DeliverableItem.vue';
import type { DeliverableStatus } from '@/services/deliverables/deliverables.types';

defineProps<{
  displayedDeliverables: {
    id: number;
    title: string;
    status: DeliverableStatus;
    fileFormat: string;
    fileSize?: string;
    externalUrl?: string | null;
  }[];
}>();

defineEmits<{
  downloadDeliverable: [deliverableId: number];
}>();
</script>
