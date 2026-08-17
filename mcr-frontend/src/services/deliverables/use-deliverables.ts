import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query';
import { QUERY_KEYS } from '@/plugins/vue-query';
import { useDeliverableFeedbackDraft } from '@/services/deliverable-feedback/use-deliverable-feedback-draft';
import {
  createDeliverable,
  downloadDeliverableFile,
  getMeetingDeliverables,
} from './deliverables.service';
import type { DeliverableCreateRequest, DeliverableDto } from './deliverables.types';

const POLLING_INTERVAL = 10 * 1000;

export function shouldPollDeliverables(deliverables?: DeliverableDto[]): boolean {
  if (!deliverables) return false;
  return deliverables.some(
    (d) => d.status === 'REQUESTED' || d.status === 'PENDING' || d.status === 'IN_PROGRESS',
  );
}

function getDeliverablesQuery(meetingId: number) {
  const drafts = useDeliverableFeedbackDraft();

  const query = useQuery({
    queryKey: [QUERY_KEYS.DELIVERABLES, meetingId],
    queryFn: () => getMeetingDeliverables(meetingId),
    select: (data) => data.deliverables,
    refetchInterval: (query) =>
      shouldPollDeliverables(query.state.data?.deliverables) ? POLLING_INTERVAL : false,
  });

  watch(query.data, (deliverables) => {
    if (deliverables !== undefined) drafts.seed(deliverables);
  });

  return query;
}

function createDeliverableMutation(meetingId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: DeliverableCreateRequest) => createDeliverable(payload),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.DELIVERABLES, meetingId] }),
  });
}

function downloadDeliverableMutation() {
  return useMutation({
    mutationFn: (deliverableId: number) => downloadDeliverableFile(deliverableId),
  });
}

export function useDeliverables() {
  return {
    getDeliverablesQuery,
    createDeliverableMutation,
    downloadDeliverableMutation,
  };
}
