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

  // Absent entries only. The deliverables list is polled every 10s, and overwriting would
  // replace what the user is typing right now with the value already saved in base.
  function seed(deliverables: DeliverableDto[]): void {
    for (const { id, feedback } of deliverables) {
      if (feedback === null || id in drafts.value) continue;
      drafts.value[id] = {
        vote_type: feedback.vote_type,
        comment: feedback.comment ?? '',
        reasons: [...feedback.reasons],
      };
    }
  }

  function remember(deliverableId: number, draft: DeliverableFeedbackDraft): void {
    drafts.value[deliverableId] = { ...draft, reasons: [...draft.reasons] };
  }

  function forget(deliverableId: number): void {
    delete drafts.value[deliverableId];
  }

  return { draftFor, seed, remember, forget };
});
