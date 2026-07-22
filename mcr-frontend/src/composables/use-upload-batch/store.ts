import type { UploadFailureType } from '@/services/http/http.utils';
import {
  getExecutionOrder,
  getItem,
  getTranscodingItems,
  getUploadingItems,
  isSettledItem,
} from './selectors';

export const MAX_CONCURRENT_UPLOADS = 1;
export const MAX_CONCURRENT_TRANSCODES = 1;
export const ETA_SMOOTHING_ALPHA = 0.3;

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

export function createInitialState(): UploadState {
  return {
    items: [],
    nextId: 1,
    nextBatchId: 1,
    bytesPerSecond: null,
    transcodeSecondsPerSecond: null,
  };
}

export function enqueue(
  state: UploadState,
  drafts: UploadDraft[],
): { state: UploadState; itemIds: number[] } {
  if (drafts.length === 0) {
    return { state, itemIds: [] };
  }

  const newItems: UploadItem[] = drafts.map((draft, index) => ({
    id: state.nextId + index,
    batchId: state.nextBatchId,
    title: draft.title,
    kind: draft.kind,
    durationSeconds: draft.durationSeconds,
    totalBytes: draft.totalBytes,
    sentBytes: 0,
    meetingId: null,
    status: draft.kind === 'video' ? 'transcode-pending' : 'upload-pending',
    failureType: null,
    transcodeRatio: 0,
  }));

  return {
    state: {
      ...state,
      items: [...state.items, ...newItems],
      nextId: state.nextId + drafts.length,
      nextBatchId: state.nextBatchId + 1,
    },
    itemIds: newItems.map((item) => item.id),
  };
}

export function promote(state: UploadState): UploadState {
  let uploadSlots = MAX_CONCURRENT_UPLOADS - getUploadingItems(state).length;
  let transcodeSlots = MAX_CONCURRENT_TRANSCODES - getTranscodingItems(state).length;

  const promotions = new Map<number, UploadItemStatus>();
  for (const item of getExecutionOrder(state)) {
    if (uploadSlots > 0 && isReadyToUpload(item)) {
      promotions.set(item.id, 'uploading');
      uploadSlots--;
    } else if (transcodeSlots > 0 && item.status === 'transcode-pending') {
      promotions.set(item.id, 'transcoding');
      transcodeSlots--;
    }
  }

  if (promotions.size === 0) {
    return state;
  }

  return {
    ...state,
    items: state.items.map((item) => {
      const promotedStatus = promotions.get(item.id);
      return promotedStatus ? { ...item, status: promotedStatus } : item;
    }),
  };
}

export function attachMeeting(state: UploadState, id: number, meetingId: number): UploadState {
  const item = getItem(state, id);
  if (!item || isSettledItem(item)) {
    return state;
  }

  return replaceItem(state, { ...item, meetingId });
}

export function finishTranscode(state: UploadState, id: number, mp3Bytes: number): UploadState {
  const item = getItem(state, id);
  if (!item || item.status !== 'transcoding') {
    return state;
  }

  return replaceItem(state, { ...item, status: 'upload-pending', totalBytes: mp3Bytes });
}

export function recordProgress(
  state: UploadState,
  id: number,
  sentBytes: number,
  deltaSeconds: number,
): UploadState {
  const item = getItem(state, id);
  if (!item || item.status !== 'uploading') {
    return state;
  }

  const next = replaceItem(state, { ...item, sentBytes });

  const deltaBytes = sentBytes - item.sentBytes;
  if (deltaSeconds <= 0 || deltaBytes <= 0) {
    return next;
  }

  return {
    ...next,
    bytesPerSecond: smoothThroughput(state.bytesPerSecond, deltaBytes / deltaSeconds),
  };
}

export function recordTranscodeProgress(
  state: UploadState,
  id: number,
  ratio: number,
  deltaSeconds: number,
): UploadState {
  const item = getItem(state, id);
  if (!item || item.status !== 'transcoding') {
    return state;
  }

  const clampedRatio = Math.min(1, Math.max(item.transcodeRatio, ratio));
  const next = replaceItem(state, { ...item, transcodeRatio: clampedRatio });

  const deltaRatio = clampedRatio - item.transcodeRatio;
  if (item.durationSeconds === null || deltaSeconds <= 0 || deltaRatio <= 0) {
    return next;
  }

  const mediaSecondsDone = deltaRatio * item.durationSeconds;
  return {
    ...next,
    transcodeSecondsPerSecond: smoothThroughput(
      state.transcodeSecondsPerSecond,
      mediaSecondsDone / deltaSeconds,
    ),
  };
}

export function complete(state: UploadState, id: number): UploadState {
  const item = getItem(state, id);
  if (!item || isSettledItem(item)) {
    return state;
  }

  return replaceItem(state, { ...item, status: 'done', sentBytes: item.totalBytes });
}

export function fail(state: UploadState, id: number, failureType: UploadFailureType): UploadState {
  const item = getItem(state, id);
  if (!item || isSettledItem(item)) {
    return state;
  }

  return replaceItem(state, { ...item, status: 'error', failureType });
}

export function clearAll(state: UploadState): UploadState {
  return { ...state, items: [] };
}

function replaceItem(state: UploadState, updated: UploadItem): UploadState {
  return {
    ...state,
    items: state.items.map((item) => (item.id === updated.id ? updated : item)),
  };
}

function isReadyToUpload(item: UploadItem): boolean {
  return item.status === 'upload-pending' && item.meetingId !== null;
}

function smoothThroughput(previous: number | null, instantaneous: number): number {
  if (previous === null) {
    return instantaneous;
  }

  return ETA_SMOOTHING_ALPHA * instantaneous + (1 - ETA_SMOOTHING_ALPHA) * previous;
}
