import type { UploadFailureType } from '@/services/http/http.utils';

export type UploadKind = 'audio' | 'video';

export type UploadItemStatus =
  | 'transcode-pending'
  | 'transcoding'
  | 'upload-pending'
  | 'uploading'
  | 'done'
  | 'error';

export type UploadDraft = {
  title: string;
  kind: UploadKind;
  durationSeconds: number | null;
  totalBytes: number;
};

export type UploadItem = {
  id: number;
  batchId: number;
  title: string;
  kind: UploadKind;
  durationSeconds: number | null;
  totalBytes: number;
  sentBytes: number;
  meetingId: number | null;
  status: UploadItemStatus;
  failureType: UploadFailureType | null;
  transcodeRatio: number;
};

export type UploadState = {
  items: UploadItem[];
  nextId: number;
  nextBatchId: number;
  bytesPerSecond: number | null;
  transcodeSecondsPerSecond: number | null;
};

export type BatchTitle = {
  key: string;
  params: Record<string, number>;
};

export const MAX_CONCURRENT_UPLOADS = 1;
export const MAX_CONCURRENT_TRANSCODES = 1;
export const ETA_SMOOTHING_ALPHA = 0.3;

export const ESTIMATED_MP3_BYTES_PER_SECOND = (1024 * 1024) / 60;
export const ESTIMATED_TRANSCODE_SECONDS_PER_SECOND = 5;

export const RETRYABLE_FAILURES: UploadFailureType[] = ['timeout', 'offline', 'blocked'];

export const FAILURE_MESSAGE_KEYS: Record<UploadFailureType, string> = {
  offline: 'meeting.import.errors.connection',
  blocked: 'meeting.import.errors.connection',
  timeout: 'meeting.import.errors.server',
  'http-server': 'meeting.import.errors.server',
  unknown: 'meeting.import.errors.server',
  'http-client': 'meeting.import.errors.file-unprocessable',
  auth: 'meeting.import.errors.session-expired',
};
