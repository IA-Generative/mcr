<template>
  <div class="deliverable-type-card">
    <p
      class="m-0 text-sm font-bold text-blue-france-sun"
      :class="{ 'opacity-50': hasError }"
    >
      {{ title }}
    </p>

    <p class="m-0 flex-1 text-xs text-(--text-default-grey)">{{ description }}</p>

    <div class="flex min-h-10 items-center justify-between gap-1">
      <div class="flex items-center gap-1">
        <DeliverableFeedbackThumbs
          v-if="isAvailable && deliverable"
          :deliverable="deliverable"
        />
      </div>

      <DeliverableTypeCardActions
        :state="state"
        :deliverable="deliverable"
        :is-custom="isCustom"
        :can-regenerate="canRegenerate"
        :error-tag-label="errorTagLabel"
        :action-label="actionLabel"
        @action="onAction"
        @customize="$emit('customize')"
        @download="(id) => $emit('download', id)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { t } from '@/plugins/i18n';
import type { DeliverableDto, DeliverableType } from '@/services/deliverables/deliverables.types';
import DeliverableFeedbackThumbs from './deliverable-feedback/DeliverableFeedbackThumbs.vue';
import DeliverableTypeCardActions from './DeliverableTypeCardActions.vue';
import type { DeliverableCardState } from './deliverable-card-state';

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

const TYPE_KEY_MAP: Record<DeliverableType, string> = {
  TRANSCRIPTION: 'transcription',
  STRUCTURED_MINUTES: 'structured-minutes',
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

const state = computed<DeliverableCardState>(() => {
  if (hasError.value) return 'error';
  if (isAvailable.value) return 'available';
  if (isWaiting.value) return 'waiting';
  if (isLoading.value) return 'loading';
  if (canGenerate.value) return 'generate';
  return 'none';
});

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
</style>
