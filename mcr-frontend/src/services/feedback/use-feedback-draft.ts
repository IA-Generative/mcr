import type { VoteType } from './feedback.types';

const voteType = ref<VoteType | null>(null);
const comment = ref('');

export function useFeedbackDraft() {
  function reset() {
    voteType.value = null;
    comment.value = '';
  }

  return { voteType, comment, reset };
}
