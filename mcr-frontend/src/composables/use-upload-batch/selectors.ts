import type { UploadFailureType } from '@/services/http/http.utils';
import type { UploadItem, UploadState } from './store';

export const ESTIMATED_VIDEO_BYTES_PER_SECOND = (1024 * 1024) / 60;
export const ESTIMATED_TRANSCODE_SECONDS_PER_SECOND = 5;

export type BatchTitle = {
  key: string;
  params: Record<string, number>;
};

export function getItem(state: UploadState, id: number): UploadItem | undefined {
  return state.items.find((item) => item.id === id);
}

export function getExecutionOrder(state: UploadState): UploadItem[] {
  return [...state.items].sort(byExecutionPriority);
}

export function getDisplayOrder(state: UploadState): UploadItem[] {
  return [...state.items].sort(byDisplayPriority);
}

export function getUploadingItems(state: UploadState): UploadItem[] {
  return state.items.filter((item) => item.status === 'uploading');
}

export function getTranscodingItems(state: UploadState): UploadItem[] {
  return state.items.filter((item) => item.status === 'transcoding');
}

export function isOpen(state: UploadState): boolean {
  return state.items.length > 0;
}

export function isSoleItem(state: UploadState, id: number): boolean {
  return state.items.length === 1 && state.items[0].id === id;
}

export function hasActiveWork(state: UploadState): boolean {
  return state.items.some((item) => !isSettledItem(item));
}

export function isSettled(state: UploadState): boolean {
  return state.items.length > 0 && state.items.every(isSettledItem);
}

export function isSettledItem(item: UploadItem): boolean {
  return item.status === 'done' || item.status === 'error';
}

export function getProgressRatio(item: UploadItem): number {
  return item.totalBytes === 0 ? 0 : item.sentBytes / item.totalBytes;
}

export function getBatchEtaSeconds(state: UploadState): number | null {
  const remainingMediaSeconds = state.items.reduce(
    (sum, item) => sum + getRemainingTranscodeSeconds(item),
    0,
  );

  if (!hasActiveWork(state) || (state.bytesPerSecond === null && remainingMediaSeconds === 0)) {
    return null;
  }

  const remainingBytes = state.items.reduce((sum, item) => sum + getRemainingBytes(item), 0);
  const uploadSeconds = state.bytesPerSecond === null ? 0 : remainingBytes / state.bytesPerSecond;

  const transcodeSpeed = state.transcodeSecondsPerSecond ?? ESTIMATED_TRANSCODE_SECONDS_PER_SECOND;
  const transcodeSeconds = remainingMediaSeconds / transcodeSpeed;

  return uploadSeconds + transcodeSeconds;
}

export function getBatchTitle(state: UploadState): BatchTitle | null {
  if (state.items.length === 0) {
    return null;
  }

  if (hasActiveWork(state)) {
    return { key: 'meeting.import.batch.title-active', params: { count: state.items.length } };
  }

  const errorCount = state.items.filter((item) => item.status === 'error').length;
  const successCount = state.items.length - errorCount;

  return errorCount > 0
    ? {
        key: 'meeting.import.batch.title-settled-with-errors',
        params: { success: successCount, failed: errorCount },
      }
    : { key: 'meeting.import.batch.title-settled', params: { success: successCount } };
}

const FAILURE_MESSAGE_KEYS: Record<UploadFailureType, string> = {
  offline: 'meeting.import.errors.connection',
  blocked: 'meeting.import.errors.connection',
  timeout: 'meeting.import.errors.server',
  'http-server': 'meeting.import.errors.server',
  unknown: 'meeting.import.errors.server',
  'http-client': 'meeting.import.errors.file-unprocessable',
};

export function getFailureMessageKey(item: UploadItem): string | null {
  if (item.status !== 'error' || item.failureType === null) {
    return null;
  }

  return FAILURE_MESSAGE_KEYS[item.failureType];
}

function byExecutionPriority(a: UploadItem, b: UploadItem): number {
  if (a.durationSeconds === null && b.durationSeconds === null) {
    return a.id - b.id;
  }
  if (a.durationSeconds === null) {
    return 1;
  }
  if (b.durationSeconds === null) {
    return -1;
  }

  return a.durationSeconds - b.durationSeconds || a.id - b.id;
}

function byDisplayPriority(a: UploadItem, b: UploadItem): number {
  return b.batchId - a.batchId || byExecutionPriority(a, b);
}

function getRemainingBytes(item: UploadItem): number {
  switch (item.status) {
    case 'upload-pending':
    case 'uploading':
      return item.totalBytes - item.sentBytes;
    case 'transcode-pending':
    case 'transcoding':
      return item.durationSeconds !== null
        ? item.durationSeconds * ESTIMATED_VIDEO_BYTES_PER_SECOND
        : item.totalBytes;
    case 'done':
    case 'error':
      return 0;
  }
}

function getRemainingTranscodeSeconds(item: UploadItem): number {
  if (item.durationSeconds === null) {
    return 0;
  }
  switch (item.status) {
    case 'transcode-pending':
      return item.durationSeconds;
    case 'transcoding':
      return (1 - item.transcodeRatio) * item.durationSeconds;
    default:
      return 0;
  }
}
