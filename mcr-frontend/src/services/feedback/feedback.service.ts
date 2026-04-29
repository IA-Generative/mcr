import HttpService, { API_PATHS } from '../http/http.service';
import type { FeedbackPayload, FeedbackPromise } from './feedback.types';

export async function create(payload: FeedbackPayload): Promise<FeedbackPromise> {
  const { data } = await HttpService.post(`${API_PATHS.FEEDBACKS}`, payload);
  return data;
}
