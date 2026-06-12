<template>
  <BaseModal
    modal-id="feedback-modal"
    :title="modalTitle"
    no-actions
  >
    <template v-if="step === 1">
      <p class="fr-text--sm">{{ t('feedback.modal.body') }}</p>
      <DsfrRadioButtonSet
        v-model="voteType"
        name="feedback-vote"
        inline
        :options="voteOptions"
        class="vote-options mb-4"
      />

      <Transition name="slide-down">
        <DsfrInputGroup
          v-if="showTextInput"
          v-model="comment"
          v-bind="commentAttrs"
          :placeholder="t('feedback.comment.placeholder')"
          :label="t('feedback.comment.label')"
          :label-visible="true"
          :error-message="errors.comment"
          is-textarea
          rows="3"
          class="comment-input"
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
import thumbDownIcon from '@gouvfr/dsfr/dist/icons/system/thumb-down-line.svg?url';
import thumbUpIcon from '@gouvfr/dsfr/dist/icons/system/thumb-up-line.svg?url';
import useToaster from '@/composables/use-toaster';
import { t } from '@/plugins/i18n';
import { createFeedbackMutation } from '@/services/feedback/use-feedback';
import { useFeedbackDraft } from '@/services/feedback/use-feedback-draft';
import { toTypedSchema } from '@vee-validate/yup';
import { useForm, useIsFormValid } from 'vee-validate';
import { useVfm } from 'vue-final-modal';
import { useRoute } from 'vue-router';
import { FeedbackSchema } from './feedback.schema';

const DELAY_TO_SHOW_THANKS = 2000; // 2 seconds

const route = useRoute();
const toaster = useToaster();
const draft = useFeedbackDraft();
const mutation = createFeedbackMutation();

const { defineField, values, errors, handleSubmit } = useForm({
  validationSchema: toTypedSchema(FeedbackSchema),
  initialValues: {
    vote_type: draft.voteType.value ?? undefined,
    comment: draft.comment.value,
  },
  validateOnMount: true,
});

const [comment, commentAttrs] = defineField('comment');
const [voteType] = defineField('vote_type');
const isFormValid = useIsFormValid();

const voteOptions = [
  { label: t('feedback.vote.positive'), value: 'POSITIVE', rich: true, img: thumbUpIcon },
  { label: t('feedback.vote.negative'), value: 'NEGATIVE', rich: true, img: thumbDownIcon },
];

// Sync the form back into the draft so the text survives the modal closing.
// No loop: the draft only feeds the form once, through initialValues.
watch(values, (newValues) => {
  draft.voteType.value = newValues.vote_type ?? null;
  draft.comment.value = newValues.comment ?? '';
});

let thanksTimeout: ReturnType<typeof setTimeout> | null = null;

onUnmounted(() => {
  if (thanksTimeout) clearTimeout(thanksTimeout);
});

const submitFeedback = handleSubmit((formValues) => {
  mutation.mutate(
    {
      vote_type: formValues.vote_type,
      comment: formValues.comment || undefined,
      url: route.fullPath,
    },
    {
      onSuccess: () => {
        draft.reset();
        // Show thanks
        step.value = 2;
        // Close modal. In thanksTimeout to clear timeout if you close modal before the end of timeout.
        thanksTimeout = setTimeout(() => {
          useVfm().close('feedback-modal');
        }, DELAY_TO_SHOW_THANKS);
      },
      onError: () => toaster.addErrorMessage(t('error.default')),
    },
  );
});

const step = ref<1 | 2>(1);

const modalTitle = computed(() =>
  step.value === 1 ? t('feedback.modal.title') : t('feedback.success.title'),
);
const showTextInput = computed(() => !!voteType.value);
const sentIsButtonDisabled = computed(() => !isFormValid.value || mutation.isPending.value);
</script>

<style scoped>
.vote-options :deep(.fr-fieldset__element--inline) {
  flex: 1 1 0;
}

.vote-options :deep(.fr-radio-rich) {
  width: 100%;
}
</style>
