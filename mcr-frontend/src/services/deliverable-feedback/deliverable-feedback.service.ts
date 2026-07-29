import HttpService, { API_PATHS } from '../http/http.service';
import type {
  DeliverableFeedbackDto,
  DeliverableFeedbackPayload,
} from './deliverable-feedback.types';

export async function upsertDeliverableFeedback(
  deliverableId: number,
  payload: DeliverableFeedbackPayload,
): Promise<DeliverableFeedbackDto> {
  const { data } = await HttpService.put<DeliverableFeedbackDto>(
    `${API_PATHS.DELIVERABLES}/${deliverableId}/feedback`,
    payload,
  );
  return data;
}

export async function deleteDeliverableFeedback(deliverableId: number): Promise<void> {
  await HttpService.delete(`${API_PATHS.DELIVERABLES}/${deliverableId}/feedback`);
}
