<template>
  <li class="row flex items-center justify-between gap-4 px-4 py-3">
    <span class="truncate font-medium">{{ item.title }}</span>
    <ImportStatusIndicator :item="item" />
  </li>
</template>

<script lang="ts" setup>
import ImportStatusIndicator from '@/components/import/ImportStatusIndicator.vue';
import type { UploadItem } from '@/composables/use-upload-batch';

defineProps<{ item: UploadItem }>();
</script>

<style scoped>
.row {
  border-top: 1px solid var(--border-default-grey, #ddd);
}
</style>
