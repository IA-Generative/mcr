<template>
  <BaseModal
    :modal-id="MODAL_ID"
    :title="$t('meeting-v2.deliverable-feedback.negative-modal.title')"
    size="lg"
    no-actions
    disable-close-on-outside-click
    @closed="emit('closed')"
  >
    <div class="flex flex-col gap-4">
      <p class="m-0 text-grey">
        {{ $t('meeting-v2.deliverable-feedback.negative-modal.description') }}
      </p>

      <div class="flex flex-col gap-2">
        <span class="text-xs font-bold text-grey-mention">
          {{ $t('meeting-v2.deliverable-feedback.negative-modal.reasons-label').toUpperCase() }}
        </span>

        <p
          v-if="isLoadingReasons"
          class="m-0 text-sm text-grey-mention"
        >
          {{ $t('meeting-v2.deliverable-feedback.negative-modal.reasons-loading') }}
        </p>

        <div
          v-else-if="areReasonsUnavailable"
          class="flex flex-col items-start gap-2"
        >
          <p class="m-0 text-sm text-error-425">
            {{ $t('meeting-v2.deliverable-feedback.negative-modal.reasons-unavailable') }}
          </p>
          <DsfrButton
            size="sm"
            secondary
            :label="$t('meeting-v2.deliverable-feedback.negative-modal.retry')"
            @click="() => refetch()"
          />
        </div>

        <DsfrTags
          v-else
          v-model="selectedReasons"
          :tags="reasonTags"
        />
      </div>

      <div class="flex flex-col gap-1">
        <label
          for="deliverable-negative-feedback-comment"
          class="text-xs font-bold text-grey-mention"
        >
          {{ $t('meeting-v2.deliverable-feedback.negative-modal.comment-label').toUpperCase() }}
        </label>
        <textarea
          id="deliverable-negative-feedback-comment"
          v-model="comment"
          class="fr-input resize-y overflow-y-auto"
          rows="4"
          :placeholder="$t('meeting-v2.deliverable-feedback.negative-modal.comment-placeholder')"
        />
        <p
          v-if="violation"
          class="m-0 text-sm text-error-425"
        >
          {{ $t(`meeting-v2.deliverable-feedback.negative-modal.errors.${violation}`) }}
        </p>
      </div>
    </div>

    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <DsfrButton
          :label="$t('meeting-v2.deliverable-feedback.negative-modal.submit')"
          :disabled="!canSubmit"
          @click="onSubmitClick"
        />
      </div>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import type { DeliverableType } from '@/services/deliverables/deliverables.types';
import { useDeliverableFeedbackReasons } from '@/services/deliverable-feedback/use-deliverable-feedback-reasons';
import { negativeFeedbackViolation } from './negative-feedback.rules';
import { reasonLabel } from './reason-label';

const MODAL_ID = 'deliverable-negative-feedback-modal';

export interface NegativeFeedbackDraft {
  reasons: string[];
  comment: string;
}

const props = defineProps<{
  deliverableType: DeliverableType;
  isSubmitting: boolean;
  initialReasons?: string[];
  initialComment?: string;
  onSubmit: (draft: NegativeFeedbackDraft) => void;
  onUpdateDraft: (draft: NegativeFeedbackDraft) => void;
}>();

const emit = defineEmits<{ closed: [] }>();

const {
  data: catalogue,
  isLoading: isLoadingReasons,
  isError,
  refetch,
} = useDeliverableFeedbackReasons();

const selectedReasons = ref<string[]>([...(props.initialReasons ?? [])]);
const comment = ref(props.initialComment ?? '');
const hasTriedToSubmit = ref(false);

watch([selectedReasons, comment], () =>
  props.onUpdateDraft({ reasons: selectedReasons.value, comment: comment.value }),
);

const offered = computed(() => catalogue.value?.[props.deliverableType]);

const areReasonsUnavailable = computed(
  () => !isLoadingReasons.value && (isError.value || offered.value === undefined),
);

const canSubmit = computed(
  () => !props.isSubmitting && !isLoadingReasons.value && !areReasonsUnavailable.value,
);

const reasonTags = computed(() => {
  const entry = offered.value;
  if (entry === undefined) return [];
  return entry.reasons.map((reason) => ({
    label: reasonLabel(entry.deliverable_group, reason),
    value: reason,
    selectable: true as const,
    // The API between DSFRTags and DSFRTag differs. The first one selects the tags based on the model-value
    // The second one uses props only.
    // But the DSFRTags repackages the props of the DSFRTag as DSFRTagProps[] => Hence the need for this patch
    selected: undefined,
  }));
});

const violation = computed(() =>
  hasTriedToSubmit.value
    ? negativeFeedbackViolation({ reasons: selectedReasons.value, comment: comment.value })
    : null,
);

function onSubmitClick(): void {
  if (!canSubmit.value) return;

  hasTriedToSubmit.value = true;
  if (violation.value !== null) return;

  props.onSubmit({ reasons: selectedReasons.value, comment: comment.value });
}
</script>
