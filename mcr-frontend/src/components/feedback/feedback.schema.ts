import yup from '@/config/yup';
import { t } from '@/plugins/i18n';
import { FEEDBACK_COMMENT_MAX_LENGTH, VoteType } from '@/services/feedback/feedback.types';

export interface FeedbackFields {
  vote_type: VoteType;
  comment?: string;
}

export const FeedbackSchema: yup.ObjectSchema<FeedbackFields> = yup.object({
  vote_type: yup.string<VoteType>().oneOf(VoteType).required(),
  comment: yup
    .string()
    .max(FEEDBACK_COMMENT_MAX_LENGTH, ({ value, max }) =>
      t('feedback.comment.error', { current: (value as string).length, max }),
    ),
});
