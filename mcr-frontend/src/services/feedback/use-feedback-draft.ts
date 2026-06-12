import type { VoteType } from './feedback.types';

// Module-level state: the draft must survive the modal closing (the modal is
// unmounted on close), and FeedbackButton remounting.
const voteType = ref<VoteType | null>(null);
const comment = ref('');

export function useFeedbackDraft() {
  function reset() {
    voteType.value = null;
    comment.value = '';
  }

  return { voteType, comment, reset };
}
