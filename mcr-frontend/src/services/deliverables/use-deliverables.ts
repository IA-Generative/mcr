import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query';
import { QUERY_KEYS } from '@/plugins/vue-query';
import {
  createDeliverable,
  downloadDeliverableFile,
  getMeetingDeliverables,
} from './deliverables.service';
import type { DeliverableCreateRequest, DeliverableResponse } from './deliverables.types';

const POLLING_INTERVAL = 10 * 1000;

function shouldPollDeliverables(deliverables?: DeliverableResponse[]): boolean {
  if (!deliverables) return false;
  return deliverables.some((d) => d.status === 'PENDING');
}

function getDeliverablesQuery(meetingId: number) {
  return useQuery({
    queryKey: [QUERY_KEYS.DELIVERABLES, meetingId],
    queryFn: () => getMeetingDeliverables(meetingId),
    select: (data) => data.deliverables,
    refetchInterval: (query) =>
      shouldPollDeliverables(query.state.data?.deliverables) ? POLLING_INTERVAL : false,
  });
}

function createDeliverableMutation(meetingId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: DeliverableCreateRequest) => createDeliverable(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.DELIVERABLES, meetingId] });
    },
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
