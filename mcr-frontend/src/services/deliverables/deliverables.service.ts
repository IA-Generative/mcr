import type { AxiosResponse } from 'axios';
import HttpService, { API_PATHS } from '../http/http.service';
import type { MeetingStatus } from '../meetings/meetings.types';
import {
  meetingStatusForReportDone,
  meetingStatusForReportFailed,
  meetingStatusForReportInProgress,
  meetingStatusForReportPending,
  meetingStatusForTranscriptionDone,
  meetingStatusForTranscriptionFailed,
  meetingStatusForTranscriptionInProgress,
  meetingStatusForTranscriptionPending,
  type DeliverableCreateRequest,
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

export function getTranscriptionStatus(status: MeetingStatus): DeliverableStatus | null {
  if (meetingStatusForTranscriptionPending.includes(status)) {
    return 'PENDING';
  }
  if (meetingStatusForTranscriptionInProgress.includes(status)) {
    return 'IN_PROGRESS';
  }
  if (meetingStatusForTranscriptionDone.includes(status)) {
    return 'AVAILABLE';
  }
  if (meetingStatusForTranscriptionFailed.includes(status)) {
    return 'FAILED';
  }
  return null;
}

export function getReportStatus(status: MeetingStatus): DeliverableStatus | null {
  if (meetingStatusForReportPending.includes(status)) {
    return 'PENDING';
  }
  if (meetingStatusForReportInProgress.includes(status)) {
    return 'IN_PROGRESS';
  }
  if (meetingStatusForReportDone.includes(status)) {
    return 'AVAILABLE';
  }
  if (meetingStatusForReportFailed.includes(status)) {
    return 'FAILED';
  }
  return null;
}
