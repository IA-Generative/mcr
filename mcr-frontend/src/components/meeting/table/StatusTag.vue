<template>
  <DsfrTag
    v-if="tagMeta"
    :label="tagMeta.label"
    :class="tagMeta.class"
    :icon="tagMeta.icon"
    small
  />
</template>

<script lang="ts">
import { t } from '@/plugins/i18n';
import type { DeliverableStatus } from '@/services/deliverables/deliverables.types';

interface TagMeta {
  class: string;
  label: string;
  icon: string;
}

export function getTagMeta(status: DeliverableStatus | null): TagMeta | null {
  if (status === 'PENDING') {
    return {
      class: 'bg-info-950 text-info-425',
      label: t('meetings_v2.table.columns.status.pending'),
      icon: 'fr-icon-info-fill',
    };
  }
  if (status === 'IN_PROGRESS') {
    return {
      class: 'bg-yellow-tournesol-950 text-yellow-tournesol-sun',
      label: t('meetings_v2.table.columns.status.info'),
      icon: 'fr-icon-flashlight-fill',
    };
  }
  if (status === 'DONE') {
    return {
      class: 'bg-success-950 text-success-425',
      label: t('meetings_v2.table.columns.status.success'),
      icon: 'fr-icon-success-fill',
    };
  }
  if (status === 'FAILED') {
    return {
      class: 'bg-error-950 text-error-425',
      label: t('meetings_v2.table.columns.status.error'),
      icon: 'fr-icon-error-fill',
    };
  }
  return null;
}
</script>

<script lang="ts" setup>
const props = defineProps<{
  status: DeliverableStatus | null;
}>();

const tagMeta = computed(() => getTagMeta(props.status));
</script>
