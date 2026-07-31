<template>
  <div class="flex items-center gap-1">
    <button
      type="button"
      class="feedback-thumb fr-btn fr-btn--tertiary-no-outline"
      :class="isPositive ? 'fr-icon-thumb-up-fill text-success-425' : 'fr-icon-thumb-up-line'"
      :aria-pressed="isPositive"
      :title="$t('meeting-v2.deliverable-feedback.thumb-up')"
      @click="onThumbUpClick"
    >
      <span class="sr-only">{{ $t('meeting-v2.deliverable-feedback.thumb-up') }}</span>
    </button>
    <button
      type="button"
      class="feedback-thumb fr-btn fr-btn--tertiary-no-outline"
      :class="isNegative ? 'fr-icon-thumb-down-fill text-error-425' : 'fr-icon-thumb-down-line'"
      :aria-pressed="isNegative"
      :title="$t('meeting-v2.deliverable-feedback.thumb-down')"
      @click="onThumbDownClick"
    >
      <span class="sr-only">{{ $t('meeting-v2.deliverable-feedback.thumb-down') }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { useModal } from 'vue-final-modal';
import useToaster from '@/composables/use-toaster';
import { t } from '@/plugins/i18n';
import type { DeliverableDto } from '@/services/deliverables/deliverables.types';
import type { VoteType } from '@/services/feedback/feedback.types';
import type { DeliverableFeedbackPayload } from '@/services/deliverable-feedback/deliverable-feedback.types';
import { useDeliverableFeedback } from '@/services/deliverable-feedback/use-deliverable-feedback';
import DeliverableFeedbackModal from './DeliverableFeedbackModal.vue';
import DeliverableNegativeFeedbackModal, {
  type NegativeFeedbackDraft,
} from './DeliverableNegativeFeedbackModal.vue';

const props = defineProps<{
  deliverable: DeliverableDto;
}>();

const toaster = useToaster();
const { upsertMutation, removeMutation } = useDeliverableFeedback(props.deliverable.meeting_id);

const previewedVote = ref<VoteType | null | undefined>(undefined);

const shownVote = computed(() =>
  previewedVote.value !== undefined
    ? previewedVote.value
    : (props.deliverable.feedback?.vote_type ?? null),
);
const isPositive = computed(() => shownVote.value === 'POSITIVE');
const isNegative = computed(() => shownVote.value === 'NEGATIVE');

watch(
  () => props.deliverable.feedback?.vote_type ?? null,
  () => {
    forgetPreview();
  },
);

const positiveModal = useModal({
  component: DeliverableFeedbackModal,
  attrs: {
    get isSubmitting() {
      return upsertMutation.isPending.value;
    },
    onSubmit: (comment: string) =>
      submitVote({ vote_type: 'POSITIVE', ...substantiveComment(comment) }),
    onClosed: () => onModalClosed(),
  },
});

const negativeModal = useModal({
  component: DeliverableNegativeFeedbackModal,
  attrs: {
    deliverableType: props.deliverable.type,
    get isSubmitting() {
      return upsertMutation.isPending.value;
    },
    onSubmit: (draft: NegativeFeedbackDraft) =>
      submitVote({
        vote_type: 'NEGATIVE',
        reasons: draft.reasons,
        ...substantiveComment(draft.comment),
      }),
    onClosed: () => onModalClosed(),
  },
});

function onThumbUpClick(): void {
  if (isPositive.value) return retractVote();
  previewVote('POSITIVE');
  positiveModal.open();
}

function onThumbDownClick(): void {
  if (isNegative.value) return retractVote();
  previewVote('NEGATIVE');
  negativeModal.open();
}

function previewVote(voteType: VoteType): void {
  if (shownVote.value === null) return;
  previewedVote.value = voteType;
}

function forgetPreview(): void {
  previewedVote.value = undefined;
}

function onModalClosed(): void {
  forgetPreview();
}

function retractVote(): void {
  removeMutation.mutate(props.deliverable.id, {
    onError: () => toaster.addErrorMessage(t('meeting-v2.deliverable-feedback.error')!),
  });
}

function substantiveComment(comment: string): { comment?: string } {
  const trimmed = comment.trim();
  return trimmed ? { comment: trimmed } : {};
}

function submitVote(payload: DeliverableFeedbackPayload): void {
  upsertMutation.mutate(
    { deliverableId: props.deliverable.id, payload },
    {
      onSuccess: () => {
        (payload.vote_type === 'POSITIVE' ? positiveModal : negativeModal).close();
        toaster.addSuccessMessage(t('meeting-v2.deliverable-feedback.success')!);
      },
      onError: () => toaster.addErrorMessage(t('meeting-v2.deliverable-feedback.error')!),
    },
  );
}
</script>

<style scoped>
.feedback-thumb::after {
  display: none;
  content: none;
}
</style>
