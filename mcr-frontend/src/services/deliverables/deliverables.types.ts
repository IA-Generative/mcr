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
  'CAPTURE_BOT_CONNECTION_FAILED',
];
export const meetingStatusForTranscriptionDone: MeetingStatus[] = [
  'TRANSCRIPTION_DONE',
  'REPORT_PENDING',
  'REPORT_DONE',
  'REPORT_FAILED',
];

export const meetingStatusForReportPending: MeetingStatus[] = [
  'NONE',
  'CAPTURE_PENDING',
  'IMPORT_PENDING',
  'CAPTURE_BOT_IS_CONNECTING',
  'CAPTURE_IN_PROGRESS',
  'CAPTURE_DONE',
  'TRANSCRIPTION_PENDING',
  'TRANSCRIPTION_IN_PROGRESS',
  'TRANSCRIPTION_DONE',
];

export const meetingStatusForReportInProgress: MeetingStatus[] = ['REPORT_PENDING'];
export const meetingStatusForReportFailed: MeetingStatus[] = [
  'CAPTURE_FAILED',
  'TRANSCRIPTION_FAILED',
  'CAPTURE_BOT_CONNECTION_FAILED',
  'REPORT_FAILED',
];
export const meetingStatusForReportDone: MeetingStatus[] = ['REPORT_DONE'];
