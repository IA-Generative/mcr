<template>
  <div
    v-if="transcriptionItem || displayedDeliverables.length"
    class="flex gap-2 flex-wrap"
  >
    <DeliverableItem
      v-if="transcriptionItem"
      class="border border-[#DDDDDD]"
      :deliverable-id="TRANSCRIPTION_ITEM_ID"
      :title="transcriptionItem.title"
      :status="transcriptionItem.status as DeliverableStatus"
      :file-format="transcriptionItem.fileFormat"
      @download="$emit('downloadTranscription')"
    />
    <DeliverableItem
      v-for="item in displayedDeliverables"
      :key="item.id"
      :deliverable-id="item.id"
      :title="item.title"
      :status="item.status as DeliverableStatus"
      :file-format="item.fileFormat"
      :file-size="item.fileSize"
      @download="$emit('downloadDeliverable', $event)"
    />
  </div>
</template>

<script setup lang="ts">
import DeliverableItem from './DeliverableItem.vue';
import type { DeliverableStatus } from '@/services/deliverables/deliverables.types';

const TRANSCRIPTION_ITEM_ID = -1;

defineProps<{
  transcriptionItem: { title: string; status: string; fileFormat: string } | null;
  displayedDeliverables: {
    id: number;
    title: string;
    status: string;
    fileFormat: string;
    fileSize?: string;
  }[];
}>();

defineEmits<{
  downloadTranscription: [];
  downloadDeliverable: [deliverableId: number];
}>();
</script>
