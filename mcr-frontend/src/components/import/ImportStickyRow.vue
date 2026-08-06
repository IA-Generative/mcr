<template>
  <li class="flex flex-col gap-1 border-t border-(--border-default-grey) px-4 py-3">
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
