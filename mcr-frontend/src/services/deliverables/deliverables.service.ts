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
  type DeliverableStatus,
} from './deliverables.types';

export function getTranscriptionStatus(status: MeetingStatus): DeliverableStatus | null {
  if (meetingStatusForTranscriptionPending.includes(status)) {
    return 'PENDING';
  }
  if (meetingStatusForTranscriptionInProgress.includes(status)) {
    return 'IN_PROGRESS';
  }
  if (meetingStatusForTranscriptionDone.includes(status)) {
    return 'DONE';
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
    return 'DONE';
  }
  if (meetingStatusForReportFailed.includes(status)) {
    return 'FAILED';
  }
  return null;
}
