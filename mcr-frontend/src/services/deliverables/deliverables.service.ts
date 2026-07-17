import type { AxiosResponse } from 'axios';
import HttpService, { API_PATHS } from '../http/http.service';
import {
  type DeliverableCreateRequest,
  type DeliverableListResponse,
  type DeliverableStatus,
  type DeliverableType,
} from './deliverables.types';

type DeliverableTag = { type: DeliverableType; status: DeliverableStatus };

const REPORT_TYPES: DeliverableType[] = ['DECISION_RECORD', 'DETAILED_SYNTHESIS', 'CUSTOM_REPORT'];

export async function getMeetingDeliverables(meetingId: number): Promise<DeliverableListResponse> {
  const { data } = await HttpService.get<DeliverableListResponse>(
    `${API_PATHS.MEETINGS}/${meetingId}/${API_PATHS.DELIVERABLES}`,
  );
  return data;
}

export async function createDeliverable(payload: DeliverableCreateRequest): Promise<void> {
  await HttpService.post(`${API_PATHS.DELIVERABLES}`, payload);
}

export async function deleteDeliverable(deliverableId: number): Promise<void> {
  await HttpService.delete(`${API_PATHS.DELIVERABLES}/${deliverableId}`);
}

export async function downloadDeliverableFile(deliverableId: number): Promise<AxiosResponse> {
  return HttpService.get(`${API_PATHS.DELIVERABLES}/${deliverableId}/file`, {
    responseType: 'blob' as const,
  });
}

export function transcriptionTag(deliverables: DeliverableTag[]): DeliverableStatus | null {
  const transcription = deliverables.find((d) => d.type === 'TRANSCRIPTION');
  return transcription ? transcription.status : 'PENDING';
}

export function reportTag(deliverables: DeliverableTag[]): DeliverableStatus | null {
  const statuses = deliverables.filter((d) => REPORT_TYPES.includes(d.type)).map((d) => d.status);
  if (statuses.length === 0) {
    return 'PENDING';
  }
  if (statuses.includes('AVAILABLE')) {
    return 'AVAILABLE';
  }
  if (statuses.includes('FAILED')) {
    return 'FAILED';
  }
  if (statuses.includes('IN_PROGRESS')) {
    return 'IN_PROGRESS';
  }
  return 'PENDING';
}
