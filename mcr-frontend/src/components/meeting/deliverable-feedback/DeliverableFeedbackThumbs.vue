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
  </div>
</template>

<script setup lang="ts">
import { useModal } from 'vue-final-modal';
import useToaster from '@/composables/use-toaster';
import { t } from '@/plugins/i18n';
import type { DeliverableDto } from '@/services/deliverables/deliverables.types';
import { useDeliverableFeedback } from '@/services/deliverable-feedback/use-deliverable-feedback';
import DeliverableFeedbackModal from './DeliverableFeedbackModal.vue';

const props = defineProps<{
  deliverable: DeliverableDto;
}>();

const toaster = useToaster();
const { upsertMutation, removeMutation } = useDeliverableFeedback(props.deliverable.meeting_id);

const isPositive = computed(() => props.deliverable.feedback?.vote_type === 'POSITIVE');

const { open, close } = useModal({
  component: DeliverableFeedbackModal,
  attrs: {
    get isSubmitting() {
      return upsertMutation.isPending.value;
    },
    onSubmit: (comment: string) => submitPositiveVote(comment),
  },
});

function onThumbUpClick(): void {
  if (isPositive.value) retractVote();
  else open();
}

function retractVote(): void {
  removeMutation.mutate(props.deliverable.id, {
    onError: () => toaster.addErrorMessage(t('meeting-v2.deliverable-feedback.error')!),
  });
}

function submitPositiveVote(comment: string): void {
  upsertMutation.mutate(
    {
      deliverableId: props.deliverable.id,
      payload: { vote_type: 'POSITIVE', comment: comment.trim() || undefined },
    },
    {
      onSuccess: () => {
        close();
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
