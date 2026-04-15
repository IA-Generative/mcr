import type { MeetingStatus } from '../meetings/meetings.types';
import {
  meetingStatusForTranscriptionDone,
  meetingStatusForTranscriptionFailed,
  meetingStatusForTranscriptionInProgress,
  meetingStatusForTranscriptionPending,
  type DeliverableStatus,
} from './deliverables.types';

export function getTranscriptionStatus(status: MeetingStatus): DeliverableStatus {
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
  return 'PENDING';
}
