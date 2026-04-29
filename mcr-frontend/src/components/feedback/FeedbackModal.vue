<template>
  <BaseModal
    modal-id="feedback-modal"
    :title="modalTitle"
    no-actions
  >
    <template v-if="step === 1">
      <p class="fr-text--sm">{{ t('feedback.modal.body') }}</p>
      <div class="flex gap-4 mb-4">
        <DsfrButton
          :label="t('feedback.vote.positive')"
          icon="fr-icon-thumb-up-line"
          :no-label="false"
          :secondary="selectedVote !== 'POSITIVE'"
          @click="onSelectVote('POSITIVE')"
        />
        <DsfrButton
          :label="t('feedback.vote.negative')"
          icon="fr-icon-thumb-down-line"
          :no-label="false"
          :secondary="selectedVote !== 'NEGATIVE'"
          @click="onSelectVote('NEGATIVE')"
        />
      </div>

      <Transition name="slide-down">
        <DsfrInputGroup
          v-if="showTextInput"
          :model-value="comment"
          :placeholder="t('feedback.comment.placeholder')"
          :label="t('feedback.comment.label')"
          :label-visible="true"
          is-textarea
          class="comment-input"
          @update:model-value="onUpdateComment"
        />
      </Transition>

      <div class="flex justify-end mt-4">
        <DsfrButton
          :label="t('feedback.submit')"
          :disabled="sentIsButtonDisabled"
          @click="submitFeedback"
        />
      </div>
    </template>

    <template v-else>
      <p class="text-center fr-text--lg">{{ t('feedback.success.body') }}</p>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { t } from '@/plugins/i18n';
import type { VoteType } from '@/services/feedback/feedback.types';
import { createFeedbackMutation } from '@/services/feedback/use-feedback';
import { useVfm } from 'vue-final-modal';
import { useRoute } from 'vue-router';

const DELAY_TO_SHOW_THANKS = 2000; // 2 seconds

const props = defineProps<{
  selectedVote: VoteType | null;
  comment: string;
  onSelectVote: (v: VoteType | null) => void;
  onUpdateComment: (v: string) => void;
  onSuccess: () => void;
  onError: () => void;
}>();

const route = useRoute();
const mutation = createFeedbackMutation();

let thanksTimeout: ReturnType<typeof setTimeout> | null = null;

onUnmounted(() => {
  if (thanksTimeout) clearTimeout(thanksTimeout);
});

function submitFeedback() {
  if (!props.selectedVote) return;
  mutation.mutate(
    {
      vote_type: props.selectedVote,
      comment: props.comment || undefined,
      url: route.fullPath,
    },
    {
      onSuccess: () => {
        // Reset vote & comment
        props.onSuccess();
        // Show thanks
        step.value = 2;
        // Close modal. In thanksTimeout to clear timeout if you close modal before the end of timeout.
        thanksTimeout = setTimeout(() => {
          useVfm().close('feedback-modal');
        }, DELAY_TO_SHOW_THANKS);
      },
      onError: () => props.onError(),
    },
  );
}
const step = ref<1 | 2>(1);

const modalTitle = computed(() =>
  step.value === 1 ? t('feedback.modal.title') : t('feedback.success.title'),
);
const showTextInput = computed(() => props.selectedVote !== null);
const sentIsButtonDisabled = computed(() => !props.selectedVote || mutation.isPending.value);
</script>
