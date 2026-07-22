<template>
  <li class="row flex items-center justify-between gap-4 px-4 py-3">
    <span class="truncate font-medium">{{ item.title }}</span>
    <span
      role="img"
      :aria-label="statusMeta.label"
      class="flex shrink-0"
      :class="statusMeta.class"
    >
      <VIcon
        :name="statusMeta.icon"
        :animation="statusMeta.animation"
      />
    </span>
  </li>
</template>

<script lang="ts">
import type { UploadItem } from '@/composables/use-upload-batch';
import { t } from '@/plugins/i18n';

interface StatusMeta {
  class: string;
  label: string;
  icon: string;
  animation?: 'spin';
}

export function getStatusMeta(status: UploadItem['status']): StatusMeta {
  if (status === 'transcode-pending' || status === 'upload-pending') {
    return {
      class: 'text-grey-mention',
      label: t('meeting.import.sticky.status.pending'),
      icon: 'ri-pause-circle-line',
    };
  }

  if (status === 'transcoding' || status === 'uploading') {
    return {
      class: 'text-blue-france-sun',
      label: t('meeting.import.sticky.status.in-progress'),
      icon: 'ri-loader-3-line',
      animation: 'spin',
    };
  }

  if (status === 'done') {
    return {
      class: 'text-success-425',
      label: t('meeting.import.sticky.status.done'),
      icon: 'ri-checkbox-circle-fill',
    };
  }

  return {
    class: 'text-error-425',
    label: t('meeting.import.sticky.status.error'),
    icon: 'ri-error-warning-fill',
  };
}
</script>

<script lang="ts" setup>
const props = defineProps<{ item: UploadItem }>();

const statusMeta = computed(() => getStatusMeta(props.item.status));
</script>

<style scoped>
.row {
  border-top: 1px solid var(--border-default-grey, #ddd);
}
</style>
