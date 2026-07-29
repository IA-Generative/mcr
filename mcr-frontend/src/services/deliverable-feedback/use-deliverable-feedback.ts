import { useMutation, useQueryClient } from '@tanstack/vue-query';
import { QUERY_KEYS } from '@/plugins/vue-query';
import {
  deleteDeliverableFeedback,
  upsertDeliverableFeedback,
} from './deliverable-feedback.service';
import type { DeliverableFeedbackPayload } from './deliverable-feedback.types';

interface UpsertVariables {
  deliverableId: number;
  payload: DeliverableFeedbackPayload;
}

export function useDeliverableFeedback(meetingId: number) {
  const queryClient = useQueryClient();

  const invalidateDeliverables = () =>
    queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.DELIVERABLES, meetingId] });

  const upsertMutation = useMutation({
    mutationFn: ({ deliverableId, payload }: UpsertVariables) =>
      upsertDeliverableFeedback(deliverableId, payload),
    onSettled: invalidateDeliverables,
  });

  const removeMutation = useMutation({
    mutationFn: (deliverableId: number) => deleteDeliverableFeedback(deliverableId),
    onSettled: invalidateDeliverables,
  });

  return { upsertMutation, removeMutation };
}
