<template>
  <BaseModal
    :modal-id="MODAL_ID"
    :title="$t('meeting-v2.deliverable-feedback.modal.title')"
    size="lg"
    no-actions
    disable-close-on-outside-click
    @closed="emit('closed')"
  >
    <div class="flex flex-col gap-4">
      <p class="text-(--text-default-grey) m-0">
        {{ $t('meeting-v2.deliverable-feedback.modal.description') }}
      </p>

      <div class="flex flex-col gap-1">
        <label
          for="deliverable-feedback-comment"
          class="text-xs font-bold text-grey-mention"
        >
          {{ $t('meeting-v2.deliverable-feedback.modal.comment-label').toUpperCase() }}
        </label>
        <textarea
          id="deliverable-feedback-comment"
          v-model="comment"
          class="fr-input overflow-y-auto resize-y"
          rows="4"
        />
      </div>
    </div>

    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <DsfrButton
          :label="$t('meeting-v2.deliverable-feedback.modal.submit')"
          :disabled="isSubmitting"
          @click="onSubmitClick"
        />
      </div>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
const MODAL_ID = 'deliverable-feedback-modal';

const props = defineProps<{
  isSubmitting: boolean;
  onSubmit: (comment: string) => void;
}>();

const emit = defineEmits<{ closed: [] }>();

const comment = ref('');

function onSubmitClick(): void {
  if (props.isSubmitting) return;
  props.onSubmit(comment.value);
}
</script>
