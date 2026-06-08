<template>
  <div
    class="deliverable-item"
    :class="{ 'is-disabled': status !== 'AVAILABLE' }"
  >
    <StatusTag :status="status" />

    <p class="text-blue-france-sun font-bold text-sm m-0">{{ title }}</p>

    <div class="flex items-center justify-between">
      <span class="text-[var(--text-default-grey)] text-xs">
        {{ fileFormat }}
        <template v-if="fileSize"> - {{ fileSize }}</template>
      </span>
      <div class="flex items-center gap-1">
        <a
          v-if="externalUrl && isFichierEnabled"
          :href="externalUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="fr-btn fr-btn--tertiary-no-outline fr-icon-eye-line"
          :title="$t('meeting-v2.deliverable-card.actions.open-external')"
        >
          <span class="sr-only">
            {{ $t('meeting-v2.deliverable-card.actions.open-external') }}
          </span>
        </a>
        <DsfrButton
          icon="fr-icon-download-line"
          icon-only
          no-outline
          tertiary
          :disabled="status !== 'AVAILABLE'"
          :title="$t('meeting-v2.deliverable-card.actions.download')"
          @click="() => $emit('download')"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useFeatureFlag } from '@/composables/use-feature-flag';
import type { DeliverableStatus } from '@/services/deliverables/deliverables.types';

defineProps<{
  deliverableId: number;
  title: string;
  status: DeliverableStatus;
  fileFormat: string;
  fileSize?: string;
  externalUrl?: string | null;
}>();

const emit = defineEmits<{ download: [id: number] }>();

const isFichierEnabled = useFeatureFlag('fichier-integration');
</script>

<style scoped>
.deliverable-item {
  border: 1px solid #dddddd;
  border-bottom: 3px solid var(--blue-france-sun-113-625);
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  background-color: var(--grey-1000-50);
  width: calc(50% - 0.25rem);
}

.deliverable-item.is-disabled {
  opacity: 0.5;
}

.deliverable-item a.fr-btn::after {
  display: none;
  content: none;
}

.deliverable-item a.fr-icon-eye-line::before {
  margin-right: 0;
}
</style>
