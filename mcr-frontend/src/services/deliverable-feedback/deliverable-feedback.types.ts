import type { VoteType } from '../feedback/feedback.types';

export interface DeliverableFeedbackDto {
  vote_type: VoteType;
  comment: string | null;
}

export interface DeliverableFeedbackPayload {
  vote_type: VoteType;
  comment?: string;
}
