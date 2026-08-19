import type { AxiosResponse } from 'axios';
import HttpService, { API_PATHS } from '../http/http.service';
import {
  type DeliverableCreateRequest,
  type DeliverableDto,
  type DeliverableListResponse,
  type DeliverableStatus,
} from './deliverables.types';

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

export function getTranscriptionStatus(
  deliverables: Pick<DeliverableDto, 'type' | 'status'>[],
): DeliverableStatus | null {
  const transcription = deliverables.find((d) => d.type === 'TRANSCRIPTION');
  return transcription ? transcription.status : 'PENDING';
}

export function getReportStatus(
  deliverables: Pick<DeliverableDto, 'type' | 'status'>[],
): DeliverableStatus | null {
  const structuredMinutes = deliverables.find((d) => d.type === 'STRUCTURED_MINUTES');
  return structuredMinutes ? structuredMinutes.status : 'PENDING';
}
