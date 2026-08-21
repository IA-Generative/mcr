import { defineStore } from 'pinia';
import type { VoteType } from './feedback.types';

export const useFeedbackDraft = defineStore('feedback-draft', () => {
  const voteType = ref<VoteType | null>(null);
  const comment = ref('');

  function reset(): void {
    voteType.value = null;
    comment.value = '';
  }

  return { voteType, comment, reset };
});
