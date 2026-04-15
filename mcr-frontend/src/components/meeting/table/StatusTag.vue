<template>
  <DsfrTag
    v-if="tagMeta.label !== ''"
    :label="tagMeta.label"
    :class="tagMeta.class"
    :icon="tagMeta.icon"
    small
  />
</template>

<script lang="ts">
import { t } from '@/plugins/i18n';
import type { DeliverableStatus } from '@/services/deliverables/deliverables.types';

export function getTagMeta(status: DeliverableStatus | null) {
  if (status === 'PENDING') {
    return {
      class: 'pending',
      label: t('meetings_v2.table.columns.status.pending'),
      icon: 'fr-icon-info-fill',
    };
  }
  if (status === 'IN_PROGRESS') {
    return {
      class: 'info',
      label: t('meetings_v2.table.columns.status.info'),
      icon: 'fr-icon-flashlight-fill',
    };
  }
  if (status === 'DONE') {
    return {
      class: 'success',
      label: t('meetings_v2.table.columns.status.success'),
      icon: 'fr-icon-success-fill',
    };
  }
  if (status === 'FAILED') {
    return {
      class: 'error',
      label: t('meetings_v2.table.columns.status.error'),
      icon: 'fr-icon-error-fill',
    };
  }
  return {
    class: 'no_data',
    label: '',
    icon: '',
  };
}
</script>

<script lang="ts" setup>
const props = defineProps<{
  status: DeliverableStatus | null;
}>();

const tagMeta = computed(() => getTagMeta(props.status));
</script>

<style>
.fr-tag.pending {
  color: var(--info-425-625);
  background-color: var(--info-950-100);
}

.fr-tag.info {
  background-color: var(--yellow-tournesol-950-100);
  color: var(--yellow-tournesol-sun-407-moon-922);
}

.fr-tag.success {
  color: var(--success-425-625);
  background-color: var(--success-950-100);
}

.fr-tag.error {
  color: var(--error-425-625);
  background-color: var(--error-950-100);
}
</style>
