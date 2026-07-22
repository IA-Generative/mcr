<template>
  <li class="row flex flex-col gap-1 px-4 py-3">
    <div class="flex items-center justify-between gap-4">
      <span class="truncate font-medium">{{ item.title }}</span>
      <ImportStatusIndicator :item="item" />
    </div>
    <p
      v-if="errorMessage"
      class="m-0 text-sm text-error-425"
    >
      {{ errorMessage }}
    </p>
  </li>
</template>

<script lang="ts" setup>
import ImportStatusIndicator from '@/components/import/ImportStatusIndicator.vue';
import { useUploadBatch, type UploadItem } from '@/composables/use-upload-batch';
import { t } from '@/plugins/i18n';

const props = defineProps<{ item: UploadItem }>();

const { getFailureMessageKey } = useUploadBatch();

const errorMessage = computed(() => {
  const key = getFailureMessageKey(props.item);
  return key ? t(key) : '';
});
</script>

<style scoped>
.row {
  border-top: 1px solid var(--border-default-grey, #ddd);
}
</style>
