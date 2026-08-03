import { OTHER_REASON } from '@/services/deliverable-feedback/deliverable-feedback.types';

export type NegativeFeedbackViolation = 'no-signal' | 'other-needs-comment';

interface NegativeFeedbackDraft {
  reasons: string[];
  comment: string;
}

export function negativeFeedbackViolation({
  reasons,
  comment,
}: NegativeFeedbackDraft): NegativeFeedbackViolation | null {
  const spelledOut = comment.trim().length > 0;
  if (reasons.length === 0 && !spelledOut) return 'no-signal';
  if (reasons.length === 1 && reasons[0] === OTHER_REASON && !spelledOut) {
    return 'other-needs-comment';
  }
  return null;
}
