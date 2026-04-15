import type { MeetingStatus } from '../meetings/meetings.types';

export const DeliverableFileType = ['TRANSCRIPTION', 'REPORT'] as const;
export type DeliverableFileType = (typeof DeliverableFileType)[number];

export const DeliverableStatus = ['PENDING', 'IN_PROGRESS', 'DONE', 'FAILED'] as const;
export type DeliverableStatus = (typeof DeliverableStatus)[number];

export const meetingStatusForTranscriptionPending: MeetingStatus[] = [
  'NONE',
  'CAPTURE_PENDING',
  'IMPORT_PENDING',
  'CAPTURE_BOT_IS_CONNECTING',
  'CAPTURE_BOT_CONNECTION_FAILED',
  'CAPTURE_IN_PROGRESS',
  'CAPTURE_DONE',
  'TRANSCRIPTION_PENDING',
];

export const meetingStatusForTranscriptionInProgress: MeetingStatus[] = [
  'TRANSCRIPTION_IN_PROGRESS',
];
export const meetingStatusForTranscriptionFailed: MeetingStatus[] = [
  'CAPTURE_FAILED',
  'TRANSCRIPTION_FAILED',
];
export const meetingStatusForTranscriptionDone: MeetingStatus[] = [
  'TRANSCRIPTION_DONE',
  'REPORT_PENDING',
  'REPORT_DONE',
];
