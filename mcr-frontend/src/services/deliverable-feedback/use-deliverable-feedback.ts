import { useMutation, useQueryClient } from '@tanstack/vue-query';
import { QUERY_KEYS } from '@/plugins/vue-query';
import type { DeliverableListResponse } from '@/services/deliverables/deliverables.types';
import {
  deleteDeliverableFeedback,
  upsertDeliverableFeedback,
} from './deliverable-feedback.service';
import type {
  DeliverableFeedbackDto,
  DeliverableFeedbackPayload,
} from './deliverable-feedback.types';

interface UpsertVariables {
  deliverableId: number;
  payload: DeliverableFeedbackPayload;
}

interface Rollback {
  previous: DeliverableListResponse | undefined;
}

export function useDeliverableFeedback(meetingId: number) {
  const queryClient = useQueryClient();
  const queryKey = [QUERY_KEYS.DELIVERABLES, meetingId];

  const invalidateDeliverables = () => queryClient.invalidateQueries({ queryKey });

  async function applyOptimistically(
    deliverableId: number,
    feedback: DeliverableFeedbackDto | null,
  ): Promise<Rollback> {
    await queryClient.cancelQueries({ queryKey });
    const previous = queryClient.getQueryData<DeliverableListResponse>(queryKey);
    queryClient.setQueryData<DeliverableListResponse>(queryKey, (current) =>
      current === undefined
        ? current
        : {
            deliverables: current.deliverables.map((deliverable) =>
              deliverable.id === deliverableId ? { ...deliverable, feedback } : deliverable,
            ),
          },
    );
    return { previous };
  }

  function rollback(context: Rollback | undefined): void {
    if (context?.previous !== undefined) {
      queryClient.setQueryData(queryKey, context.previous);
    }
  }

  const upsertMutation = useMutation<DeliverableFeedbackDto, Error, UpsertVariables, Rollback>({
    mutationFn: ({ deliverableId, payload }) => upsertDeliverableFeedback(deliverableId, payload),
    onMutate: ({ deliverableId, payload }) =>
      applyOptimistically(deliverableId, {
        vote_type: payload.vote_type,
        comment: payload.comment ?? null,
      }),
    onError: (_error, _variables, context) => rollback(context),
    onSettled: invalidateDeliverables,
  });

  const removeMutation = useMutation<void, Error, number, Rollback>({
    mutationFn: (deliverableId) => deleteDeliverableFeedback(deliverableId),
    onMutate: (deliverableId) => applyOptimistically(deliverableId, null),
    onError: (_error, _variables, context) => rollback(context),
    onSettled: invalidateDeliverables,
  });

  return { upsertMutation, removeMutation };
}
