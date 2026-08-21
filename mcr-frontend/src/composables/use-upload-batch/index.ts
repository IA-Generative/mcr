import type { UploadFailureType } from '@/services/http/http.utils';
import * as selectors from './selectors';
import * as store from './store';
import type { UploadDraft, UploadItem, UploadState } from './types';

export type { UploadDraft, UploadItem } from './types';

const state = shallowRef<UploadState>(store.createInitialState());

function dispatch(update: (current: UploadState) => UploadState): void {
  state.value = store.promote(update(state.value));
}

function enqueue(drafts: UploadDraft[]): number[] {
  const { state: next, itemIds } = store.enqueue(state.value, drafts);
  state.value = store.promote(next);
  return itemIds;
}

function attachMeeting(id: number, meetingId: number): void {
  dispatch((current) => store.attachMeeting(current, id, meetingId));
}

function finishTranscode(id: number, mp3Bytes: number): void {
  dispatch((current) => store.finishTranscode(current, id, mp3Bytes));
}

function recordProgress(id: number, sentBytes: number, deltaSeconds: number): void {
  state.value = store.recordProgress(state.value, id, sentBytes, deltaSeconds);
}

function recordTranscodeProgress(id: number, ratio: number, deltaSeconds: number): void {
  state.value = store.recordTranscodeProgress(state.value, id, ratio, deltaSeconds);
}

function complete(id: number): void {
  dispatch((current) => store.complete(current, id));
}

function fail(id: number, failureType: UploadFailureType): void {
  dispatch((current) => store.fail(current, id, failureType));
}

function retry(id: number): void {
  dispatch((current) => store.retry(current, id));
}

function clearAll(): void {
  dispatch(store.clearAll);
}

function getUploadingItems(): UploadItem[] {
  return selectors.getUploadingItems(state.value);
}

function getTranscodingItems(): UploadItem[] {
  return selectors.getTranscodingItems(state.value);
}

function getItem(id: number): UploadItem | undefined {
  return selectors.getItem(state.value, id);
}

function isSoleItem(id: number): boolean {
  return selectors.isSoleItem(state.value, id);
}

const derived = {
  isOpen: computed(() => selectors.isOpen(state.value)),
  items: computed(() => selectors.getDisplayOrder(state.value)),
  batchTitle: computed(() => selectors.getBatchTitle(state.value)),
  batchEtaSeconds: computed(() => selectors.getBatchEtaSeconds(state.value)),
  hasActiveWork: computed(() => selectors.hasActiveWork(state.value)),
  pendingMeetingIds: computed(() => selectors.getPendingMeetingIds(state.value)),
  isSettled: computed(() => selectors.isSettled(state.value)),
  getProgressRatio: selectors.getProgressRatio,
  getFailureMessageKey: selectors.getFailureMessageKey,
  isRetryableItem: selectors.isRetryableItem,
};

export function useUploadBatch() {
  return derived;
}

export function useUploadBatchWriter() {
  return {
    enqueue,
    attachMeeting,
    finishTranscode,
    recordProgress,
    recordTranscodeProgress,
    complete,
    fail,
    retry,
    clearAll,
    getUploadingItems,
    getTranscodingItems,
    getItem,
    isSoleItem,
  };
}
