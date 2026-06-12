export const FEEDBACK_COMMENT_MAX_LENGTH = 1000;

export const VoteType = ['POSITIVE', 'NEGATIVE'] as const;
export type VoteType = (typeof VoteType)[number];

export interface FeedbackPayload {
  vote_type: VoteType;
  comment?: string;
  url: string;
}

export interface FeedbackPromise {
  vote_type: VoteType;
  comment?: string;
  meeting_id?: number;
}
