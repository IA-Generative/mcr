<template>
  <li class="flex flex-col gap-1 border-t border-border px-4 py-3">
    <div class="flex items-center justify-between gap-4">
      <span class="truncate font-medium">{{ item.title }}</span>
      <div class="flex shrink-0 items-center gap-1">
        <DsfrButton
          v-if="isRetryable"
          :label="t('meeting.import.sticky.retry')"
          icon="fr-icon-refresh-line"
          icon-only
          tertiary
          no-outline
          size="sm"
          @click="emit('retry')"
        />
        <ImportStatusIndicator :item="item" />
      </div>
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
const emit = defineEmits<{ retry: [] }>();

const { getFailureMessageKey, isRetryableItem } = useUploadBatch();

const errorMessage = computed(() => {
  const key = getFailureMessageKey(props.item);
  return key ? t(key) : '';
});

const isRetryable = computed(() => isRetryableItem(props.item));
</script>
