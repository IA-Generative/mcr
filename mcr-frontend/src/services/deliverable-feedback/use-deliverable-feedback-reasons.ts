import { useQuery } from '@tanstack/vue-query';
import { QUERY_KEYS } from '@/plugins/vue-query';
import { getDeliverableFeedbackReasons } from './deliverable-feedback.service';

export function useDeliverableFeedbackReasons() {
  return useQuery({
    queryKey: [QUERY_KEYS.DELIVERABLE_FEEDBACK_REASONS],
    queryFn: getDeliverableFeedbackReasons,
    staleTime: Infinity,
    gcTime: Infinity,
  });
}
