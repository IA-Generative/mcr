import type { DeliverableType } from '../deliverables/deliverables.types';
import type { VoteType } from '../feedback/feedback.types';

export const OTHER_REASON = 'OTHER';

export type DeliverableFeedbackGroup = 'TRANSCRIPTION' | 'STRUCTURED' | 'CUSTOM';

export interface DeliverableFeedbackDto {
  vote_type: VoteType;
  comment: string | null;
  reasons: string[];
}

export type DeliverableFeedbackPayload =
  | { vote_type: 'POSITIVE'; comment?: string }
  | { vote_type: 'NEGATIVE'; comment?: string; reasons: string[] };

export interface ReasonCatalogueEntry {
  deliverable_group: DeliverableFeedbackGroup;
  reasons: string[];
}

export type ReasonCatalogue = Partial<Record<DeliverableType, ReasonCatalogueEntry>>;
