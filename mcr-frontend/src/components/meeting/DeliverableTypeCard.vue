<template>
  <div class="deliverable-type-card">
    <p
      class="text-blue-france-sun font-bold text-sm m-0"
      :class="{ 'opacity-50': hasError }"
    >
      {{ title }}
    </p>

    <p class="text-[var(--text-default-grey)] text-xs m-0 flex-1">{{ description }}</p>

    <div class="flex items-center justify-end gap-1 min-h-[2.5rem]">
      <template v-if="hasError">
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
          @click="onAction"
        />
      </template>

      <div
        v-else-if="isAvailable"
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
        v-else-if="isWaiting"
        class="deliverable-tag bg-[var(--grey-925-125)] text-[var(--text-mention-grey)]"
      >
        <span
          class="fr-icon-time-line fr-icon--sm"
          aria-hidden="true"
        />
        {{ $t('meeting-v2.deliverable-card.tag.waiting') }}
      </span>

      <span
        v-else-if="isLoading"
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
        v-else-if="canGenerate"
        icon="fr-icon-sparkling-2-line"
        size="sm"
        class="generate-button"
        @click="onAction"
      >
        {{ actionLabel }}
      </DsfrButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useFeatureFlag } from '@/composables/use-feature-flag';
import { t } from '@/plugins/i18n';
import type { DeliverableDto, DeliverableType } from '@/services/deliverables/deliverables.types';

const props = defineProps<{
  type: DeliverableType;
  deliverable?: DeliverableDto;
  isGenerating?: boolean;
  transcriptionReady?: boolean;
  transcriptionFailed?: boolean;
}>();

const emit = defineEmits<{
  generate: [];
  customize: [];
  download: [id: number];
}>();

const isFichierEnabled = useFeatureFlag('fichier-integration');

const TYPE_KEY_MAP: Record<DeliverableType, string> = {
  TRANSCRIPTION: 'transcription',
  DECISION_RECORD: 'decision-record',
  DETAILED_SYNTHESIS: 'detailed-synthesis',
  CUSTOM_REPORT: 'custom-report',
};

const isTranscription = computed(() => props.type === 'TRANSCRIPTION');
const isCustom = computed(() => props.type === 'CUSTOM_REPORT');
const status = computed(() => props.deliverable?.status ?? null);

const optimistic = computed(
  () => props.isGenerating === true && (status.value === null || status.value === 'FAILED'),
);

const isTranscriptionFailure = computed(
  () =>
    (isTranscription.value && status.value === 'FAILED') ||
    (!isTranscription.value && props.transcriptionFailed === true),
);
const hasError = computed(
  () =>
    !optimistic.value &&
    status.value !== 'AVAILABLE' &&
    (status.value === 'FAILED' || isTranscriptionFailure.value),
);
const isAvailable = computed(() => status.value === 'AVAILABLE');
const isWaiting = computed(
  () => status.value === 'REQUESTED' || (optimistic.value && !props.transcriptionReady),
);
const isLoading = computed(
  () =>
    status.value === 'PENDING' ||
    status.value === 'IN_PROGRESS' ||
    (optimistic.value && props.transcriptionReady === true),
);
const canGenerate = computed(
  () => !isTranscription.value && status.value === null && !optimistic.value,
);
const canRegenerate = computed(
  () => hasError.value && !isTranscription.value && !isTranscriptionFailure.value,
);

const title = computed(() =>
  t(`meeting-v2.deliverable-card.type.${TYPE_KEY_MAP[props.type]}.title`),
);

const errorTagLabel = computed(() => {
  if (isTranscription.value) return t('meeting-v2.deliverable-card.tag.failed');
  if (isTranscriptionFailure.value) return t('meeting-v2.deliverable-card.transcription-failed');
  return t('meeting-v2.deliverable-card.tag.error');
});

const description = computed(() => {
  if (isTranscription.value) return t('meeting-v2.deliverable-card.type.transcription.auto');
  if (isWaiting.value) return t('meeting-v2.deliverable-card.report.auto-when-ready');
  return t(`meeting-v2.deliverable-card.type.${TYPE_KEY_MAP[props.type]}.hint`);
});

const actionLabel = computed(() =>
  isCustom.value
    ? t('meeting-v2.deliverable-card.customize-button')
    : t('meeting-v2.deliverable-card.generate-button'),
);

function onAction(): void {
  if (isCustom.value) emit('customize');
  else emit('generate');
}
</script>

<style scoped>
.deliverable-type-card {
  border: 1px solid #dddddd;
  border-bottom: 3px solid var(--blue-france-sun-113-625);
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  background-color: var(--grey-1000-50);
}

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

.deliverable-type-card a.fr-btn::after {
  display: none;
  content: none;
}
</style>
