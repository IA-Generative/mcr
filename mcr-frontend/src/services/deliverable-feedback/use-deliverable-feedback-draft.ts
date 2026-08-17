import { defineStore } from 'pinia';
import type { DeliverableDto } from '../deliverables/deliverables.types';
import type { VoteType } from '../feedback/feedback.types';

export interface DeliverableFeedbackDraft {
  vote_type: VoteType;
  comment: string;
  reasons: string[];
}

export const useDeliverableFeedbackDraft = defineStore('deliverable-feedback-draft', () => {
  const drafts = ref<Record<number, DeliverableFeedbackDraft>>({});

  function draftFor(
    deliverableId: number,
    voteType: VoteType,
  ): DeliverableFeedbackDraft | undefined {
    const draft = drafts.value[deliverableId];
    if (draft === undefined || draft.vote_type !== voteType) return undefined;
    return { ...draft, reasons: [...draft.reasons] };
  }

  function seed(deliverables: DeliverableDto[]): void {
    for (const { id, feedback } of deliverables) {
      if (feedback === null) continue;
      drafts.value[id] = {
        vote_type: feedback.vote_type,
        comment: feedback.comment ?? '',
        reasons: [...feedback.reasons],
      };
    }
  }

  return { draftFor, seed };
});
