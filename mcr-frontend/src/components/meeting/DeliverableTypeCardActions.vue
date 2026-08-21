<template>
  <div class="flex items-center gap-1">
    <template v-if="state === 'error'">
      <span
        class="inline-flex items-center gap-1 rounded-full bg-error-950 px-2.5 py-0.75 text-tag font-bold text-error-425 uppercase"
      >
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
        class="fr-btn fr-btn--tertiary-no-outline fr-icon-eye-line after:hidden after:content-none"
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
      class="inline-flex items-center gap-1 rounded-full bg-grey-925 px-2.5 py-0.75 text-tag font-bold text-grey-mention uppercase"
    >
      <span
        class="fr-icon-time-line fr-icon--sm"
        aria-hidden="true"
      />
      {{ $t('meeting-v2.deliverable-card.tag.waiting') }}
    </span>

    <span
      v-else-if="state === 'loading'"
      class="inline-flex items-center gap-1 rounded-full bg-info-950 px-2.5 py-0.75 text-tag font-bold text-info-425 uppercase"
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
      class="rounded-full! shadow-raised"
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
