import { create } from './feedback.service';

import { useMutation } from '@tanstack/vue-query';
import type { FeedbackPayload } from './feedback.types';

export function createFeedbackMutation() {
  return useMutation({
    mutationFn: (values: FeedbackPayload) => create(values),
  });
}
