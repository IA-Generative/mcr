<template>
  <div class="flex items-center gap-1">
    <template v-if="state === 'error'">
      <span class="deliverable-tag bg-error-950 text-error-425">
        <span
          class="fr-icon-error-fill fr-icon--sm"
          aria-hidden="true"
        />
        {{ errorTagLabel }}
      </span>
      <DsfrButton
        v-if="canRegenerate"
        icon="fr-icon-refresh-line"
        icon-only
        no-outline
        tertiary
        :title="$t('meeting-v2.deliverable-card.actions.regenerate')"
        @click="$emit('action')"
      />
    </template>

    <div
      v-else-if="state === 'available'"
      class="flex items-center gap-1"
    >
      <DsfrButton
        v-if="isCustom"
        icon="fr-icon-refresh-line"
        icon-only
        no-outline
        tertiary
        :title="$t('meeting-v2.deliverable-card.actions.regenerate')"
        @click="$emit('customize')"
      />
      <a
        v-if="deliverable?.external_url && isFichierEnabled"
        :href="deliverable.external_url"
        target="_blank"
        rel="noopener noreferrer"
        class="fr-btn fr-btn--tertiary-no-outline fr-icon-eye-line"
        :title="$t('meeting-v2.deliverable-card.actions.open-external')"
      >
        <span class="sr-only">{{ $t('meeting-v2.deliverable-card.actions.open-external') }}</span>
      </a>
      <DsfrButton
        icon="fr-icon-download-line"
        icon-only
        no-outline
        tertiary
        :title="$t('meeting-v2.deliverable-card.actions.download')"
        @click="() => deliverable && $emit('download', deliverable.id)"
      />
    </div>

    <span
      v-else-if="state === 'waiting'"
      class="deliverable-tag bg-(--grey-925-125) text-(--text-mention-grey)"
    >
      <span
        class="fr-icon-time-line fr-icon--sm"
        aria-hidden="true"
      />
      {{ $t('meeting-v2.deliverable-card.tag.waiting') }}
    </span>

    <span
      v-else-if="state === 'loading'"
      class="deliverable-tag bg-info-950 text-info-425"
    >
      <VIcon
        name="ri-loader-3-line"
        animation="spin"
        :scale="0.9"
      />
      {{ $t('meeting-v2.deliverable-card.tag.in-progress') }}
    </span>

    <DsfrButton
      v-else-if="state === 'generate'"
      icon="fr-icon-sparkling-2-line"
      size="sm"
      class="generate-button"
      @click="$emit('action')"
    >
      {{ actionLabel }}
    </DsfrButton>
  </div>
</template>

<script setup lang="ts">
import { useFeatureFlag } from '@/composables/use-feature-flag';
import type { DeliverableDto } from '@/services/deliverables/deliverables.types';
import type { DeliverableCardState } from './deliverable-card-state';

defineProps<{
  state: DeliverableCardState;
  deliverable?: DeliverableDto;
  isCustom: boolean;
  canRegenerate: boolean;
  errorTagLabel: string;
  actionLabel: string;
}>();

defineEmits<{
  action: [];
  customize: [];
  download: [id: number];
}>();

const isFichierEnabled = useFeatureFlag('fichier-integration');
</script>

<style scoped>
.deliverable-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  border-radius: 9999px;
  padding: 0.1875rem 0.625rem;
  font-size: 0.6875rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.generate-button {
  border-radius: 9999px !important;
  box-shadow: 0 2px 6px rgba(0, 0, 40, 0.16);
}

a.fr-btn::after {
  display: none;
  content: none;
}
</style>
