import { describe, expect, it } from 'vitest';

import {
  ESTIMATED_TRANSCODE_SECONDS_PER_SECOND,
  ESTIMATED_MP3_BYTES_PER_SECOND,
  getBatchEtaSeconds,
  getBatchTitle,
  getDisplayOrder,
  getExecutionOrder,
  getFailureMessageKey,
  getProgressRatio,
  getTranscodingItems,
  getUploadingItems,
  hasActiveWork,
  isSettled,
  isSoleItem,
} from './selectors';
import {
  MAX_CONCURRENT_TRANSCODES,
  MAX_CONCURRENT_UPLOADS,
  attachMeeting,
  clearAll,
  complete,
  createInitialState,
  enqueue,
  fail,
  finishTranscode,
  promote,
  recordProgress,
  recordTranscodeProgress,
  type UploadDraft,
  type UploadItem,
  type UploadState,
} from './store';

function draft(overrides: Partial<UploadDraft> = {}): UploadDraft {
  return {
    title: 'recording',
    kind: 'audio',
    durationSeconds: 60,
    totalBytes: 1_000,
    ...overrides,
  };
}

function item(state: UploadState, id: number): UploadItem {
  const found = state.items.find((candidate) => candidate.id === id);
  if (!found) {
    throw new Error(`no item ${id} in state`);
  }
  return found;
}

function enqueueWithMeetings(
  state: UploadState,
  drafts: UploadDraft[],
): { state: UploadState; itemIds: number[] } {
  const result = enqueue(state, drafts);
  let next = result.state;
  for (const id of result.itemIds) {
    next = attachMeeting(next, id, 100 + id);
  }
  return { state: next, itemIds: result.itemIds };
}

describe('upload-batch scheduling', () => {
  it('enqueues a selection as one batch: audio waits for upload, video waits for transcode', () => {
    const { state } = enqueue(createInitialState(), [
      draft({ title: 'a', kind: 'audio' }),
      draft({ title: 'b', kind: 'video' }),
    ]);

    expect(state.items.map((i) => i.status)).toEqual(['upload-pending', 'transcode-pending']);
    expect(new Set(state.items.map((i) => i.batchId)).size).toBe(1);
    expect(state.items.every((i) => i.sentBytes === 0 && i.meetingId === null)).toBe(true);
  });

  it('never runs more than the configured number of simultaneous uploads and transcodes', () => {
    const { state } = enqueueWithMeetings(createInitialState(), [
      draft({ durationSeconds: 10 }),
      draft({ durationSeconds: 20 }),
      draft({ durationSeconds: 30 }),
      draft({ kind: 'video', durationSeconds: 40 }),
      draft({ kind: 'video', durationSeconds: 50 }),
    ]);

    const promoted = promote(state);

    expect(getUploadingItems(promoted)).toHaveLength(MAX_CONCURRENT_UPLOADS);
    expect(getTranscodingItems(promoted)).toHaveLength(MAX_CONCURRENT_TRANSCODES);
  });

  it('executes shortest-first across batches: a shorter file from a newer batch passes an older longer one', () => {
    const first = enqueueWithMeetings(createInitialState(), [draft({ durationSeconds: 300 })]);
    const second = enqueueWithMeetings(first.state, [draft({ durationSeconds: 60 })]);

    const promoted = promote(second.state);

    expect(item(promoted, second.itemIds[0]).status).toBe('uploading');
    expect(item(promoted, first.itemIds[0]).status).toBe('upload-pending');
  });

  it('executes files with unreadable duration last, in arrival order among themselves', () => {
    const { state } = enqueue(createInitialState(), [
      draft({ title: 'unknown-1', durationSeconds: null }),
      draft({ title: 'long', durationSeconds: 300 }),
      draft({ title: 'unknown-2', durationSeconds: null }),
      draft({ title: 'short', durationSeconds: 60 }),
    ]);

    expect(getExecutionOrder(state).map((i) => i.title)).toEqual([
      'short',
      'long',
      'unknown-1',
      'unknown-2',
    ]);
  });

  it('never interrupts an upload in progress when a shorter file arrives', () => {
    const first = enqueueWithMeetings(createInitialState(), [draft({ durationSeconds: 600 })]);
    const running = promote(first.state);
    const second = enqueueWithMeetings(running, [draft({ durationSeconds: 60 })]);

    const promoted = promote(second.state);

    expect(item(promoted, first.itemIds[0]).status).toBe('uploading');
    expect(item(promoted, second.itemIds[0]).status).toBe('upload-pending');
  });

  it('only uploads a file whose meeting already exists, even if a shorter one is still waiting for its meeting', () => {
    const { state, itemIds } = enqueue(createInitialState(), [
      draft({ durationSeconds: 60 }),
      draft({ durationSeconds: 300 }),
    ]);
    const withOneMeeting = attachMeeting(state, itemIds[1], 42);

    const promoted = promote(withOneMeeting);

    expect(item(promoted, itemIds[1]).status).toBe('uploading');
    expect(item(promoted, itemIds[0]).status).toBe('upload-pending');
  });

  it('keeps the upload lane idle while no queued file has a meeting yet', () => {
    const { state } = enqueue(createInitialState(), [draft(), draft()]);

    expect(getUploadingItems(promote(state))).toHaveLength(0);
  });

  it('re-inserts a transcoded video at its duration position, ahead of longer waiting audio', () => {
    const { state, itemIds } = enqueueWithMeetings(createInitialState(), [
      draft({ kind: 'video', durationSeconds: 120 }),
      draft({ durationSeconds: 300 }),
    ]);
    const [videoId, audioId] = itemIds;

    const running = promote(state);
    expect(item(running, videoId).status).toBe('transcoding');
    expect(item(running, audioId).status).toBe('uploading');

    const third = enqueueWithMeetings(complete(running, audioId), [
      draft({ durationSeconds: 240 }),
    ]);
    const reinserted = promote(finishTranscode(third.state, videoId, 500_000));

    expect(item(reinserted, videoId).status).toBe('uploading');
    expect(item(reinserted, third.itemIds[0]).status).toBe('upload-pending');
  });

  it('replaces the video size with the mp3 size after transcoding, keeping progress at zero', () => {
    const { state, itemIds } = enqueue(createInitialState(), [
      draft({ kind: 'video', durationSeconds: 120, totalBytes: 50_000_000 }),
    ]);
    const transcoded = finishTranscode(promote(state), itemIds[0], 900_000);

    expect(item(transcoded, itemIds[0])).toMatchObject({
      status: 'upload-pending',
      totalBytes: 900_000,
      sentBytes: 0,
    });
  });

  it('displays the most recent batch first while executing shortest-first overall', () => {
    const first = enqueue(createInitialState(), [
      draft({ title: 'old-short', durationSeconds: 60 }),
    ]);
    const second = enqueue(first.state, [
      draft({ title: 'new-long', durationSeconds: 300 }),
      draft({ title: 'new-unknown', durationSeconds: null }),
      draft({ title: 'new-short', durationSeconds: 120 }),
    ]);

    expect(getDisplayOrder(second.state).map((i) => i.title)).toEqual([
      'new-short',
      'new-long',
      'new-unknown',
      'old-short',
    ]);
    expect(getExecutionOrder(second.state).map((i) => i.title)).toEqual([
      'old-short',
      'new-short',
      'new-long',
      'new-unknown',
    ]);
  });

  it('promoting an already-promoted state changes nothing', () => {
    const { state } = enqueueWithMeetings(createInitialState(), [
      draft({ durationSeconds: 10 }),
      draft({ durationSeconds: 20 }),
      draft({ kind: 'video', durationSeconds: 30 }),
    ]);
    const promoted = promote(state);

    expect(promote(promoted)).toBe(promoted);
  });
});

describe('upload-batch failure isolation and guards', () => {
  it('a file failure settles that file only and leaves every other file untouched', () => {
    const { state, itemIds } = enqueueWithMeetings(createInitialState(), [
      draft({ durationSeconds: 10 }),
      draft({ durationSeconds: 20 }),
      draft({ kind: 'video', durationSeconds: 30 }),
    ]);
    const running = promote(state);

    const oneFailed = fail(running, itemIds[1], 'http-server');

    expect(item(oneFailed, itemIds[1])).toMatchObject({
      status: 'error',
      failureType: 'http-server',
    });
    expect(item(oneFailed, itemIds[0])).toEqual(item(running, itemIds[0]));
    expect(item(oneFailed, itemIds[2])).toEqual(item(running, itemIds[2]));
  });

  it.each([
    ['transcode-pending', (s: UploadState) => s],
    ['transcoding', (s: UploadState) => promote(s)],
    ['upload-pending', (s: UploadState, id: number) => finishTranscode(promote(s), id, 1_000)],
    [
      'uploading',
      (s: UploadState, id: number) =>
        promote(attachMeeting(finishTranscode(promote(s), id, 1_000), id, 42)),
    ],
  ])('a failure lands from any active status (%s)', (expectedStatus, arrange) => {
    const { state, itemIds } = enqueue(createInitialState(), [
      draft({ kind: 'video', durationSeconds: 60 }),
    ]);
    const arranged = arrange(state, itemIds[0]);
    expect(item(arranged, itemIds[0]).status).toBe(expectedStatus);

    const settled = fail(arranged, itemIds[0], 'unknown');

    expect(item(settled, itemIds[0])).toMatchObject({ status: 'error', failureType: 'unknown' });
  });

  it('ignores actions targeting unknown files or illegal transitions', () => {
    const { state, itemIds } = enqueue(createInitialState(), [draft({ kind: 'video' })]);
    const errored = fail(state, itemIds[0], 'http-client');

    expect(finishTranscode(errored, itemIds[0], 1_000)).toBe(errored);
    expect(attachMeeting(errored, itemIds[0], 42)).toBe(errored);
    expect(complete(errored, itemIds[0])).toBe(errored);
    expect(complete(errored, 999)).toBe(errored);

    const cleared = clearAll(errored);
    expect(attachMeeting(cleared, itemIds[0], 42)).toBe(cleared);
  });

  it('a completed file counts as fully sent', () => {
    const { state, itemIds } = enqueueWithMeetings(createInitialState(), [
      draft({ totalBytes: 5_000 }),
    ]);

    const done = complete(promote(state), itemIds[0]);

    expect(item(done, itemIds[0])).toMatchObject({ status: 'done', sentBytes: 5_000 });
  });

  it('clearing the queue never recycles file identities nor forgets the measured throughput', () => {
    const first = enqueueWithMeetings(createInitialState(), [draft({ totalBytes: 10_000 })]);
    const measured = recordProgress(promote(first.state), first.itemIds[0], 1_000, 1);

    const cleared = clearAll(measured);
    expect(cleared.items).toHaveLength(0);
    expect(cleared.bytesPerSecond).toBe(measured.bytesPerSecond);

    const second = enqueue(cleared, [draft()]);
    expect(second.itemIds[0]).toBeGreaterThan(first.itemIds[0]);
    expect(second.state.items[0].batchId).toBeGreaterThan(first.state.items[0].batchId);
  });
});

describe('upload-batch progress and ETA', () => {
  function uploadingState(totalBytes: number): { state: UploadState; id: number } {
    const { state, itemIds } = enqueueWithMeetings(createInitialState(), [draft({ totalBytes })]);
    return { state: promote(state), id: itemIds[0] };
  }

  it('measures throughput from the first bytes then smooths subsequent samples (EWMA α = 0.3)', () => {
    const { state, id } = uploadingState(100_000);

    const firstSample = recordProgress(state, id, 1_000, 1);
    expect(firstSample.bytesPerSecond).toBe(1_000);

    const secondSample = recordProgress(firstSample, id, 3_000, 1);
    expect(secondSample.bytesPerSecond).toBe(0.3 * 2_000 + 0.7 * 1_000);
  });

  it('gives no time estimate before any byte has left, nor once everything is settled', () => {
    const { state, id } = uploadingState(10_000);
    expect(getBatchEtaSeconds(state)).toBeNull();

    const settled = complete(recordProgress(state, id, 1_000, 1), id);
    expect(getBatchEtaSeconds(settled)).toBeNull();
  });

  it('estimates the remaining time over the whole queue, not just the current file', () => {
    const { state } = enqueueWithMeetings(createInitialState(), [
      draft({ durationSeconds: 10, totalBytes: 10_000 }),
      draft({ durationSeconds: 20, totalBytes: 5_000 }),
    ]);
    const running = promote(state);
    const uploading = getUploadingItems(running)[0];

    const sampled = recordProgress(running, uploading.id, 1_000, 1);

    expect(getBatchEtaSeconds(sampled)).toBe((9_000 + 5_000) / 1_000);
  });

  it('counts an untranscoded video for its estimated mp3 weight AND its estimated transcode time, then only its upload once transcoded', () => {
    const { state, itemIds } = enqueueWithMeetings(createInitialState(), [
      draft({ durationSeconds: 10, totalBytes: 10_000 }),
      draft({ kind: 'video', durationSeconds: 120, totalBytes: 50_000_000 }),
    ]);
    const [audioId, videoId] = itemIds;
    const sampled = recordProgress(promote(state), audioId, 1_000, 1);

    expect(getBatchEtaSeconds(sampled)).toBe(
      (9_000 + 120 * ESTIMATED_MP3_BYTES_PER_SECOND) / 1_000 +
        120 / ESTIMATED_TRANSCODE_SECONDS_PER_SECOND,
    );

    const transcoded = finishTranscode(sampled, videoId, 600_000);
    expect(getBatchEtaSeconds(transcoded)).toBe((9_000 + 600_000) / 1_000);
  });

  it('estimates the transcode time of a queued video before it has reported any progress', () => {
    const { state, itemIds } = enqueueWithMeetings(createInitialState(), [
      draft({ durationSeconds: 10, totalBytes: 10_000 }),
      draft({ kind: 'video', durationSeconds: 300, totalBytes: 50_000_000 }),
    ]);
    const sampled = recordProgress(promote(state), itemIds[0], 1_000, 1);

    const uploadSeconds = (9_000 + 300 * ESTIMATED_MP3_BYTES_PER_SECOND) / 1_000;
    const estimatedTranscodeSeconds = 300 / ESTIMATED_TRANSCODE_SECONDS_PER_SECOND;
    expect(getBatchEtaSeconds(sampled)).toBe(uploadSeconds + estimatedTranscodeSeconds);
  });

  it('estimates a video with unreadable duration by its source size', () => {
    const { state, itemIds } = enqueueWithMeetings(createInitialState(), [
      draft({ durationSeconds: 10, totalBytes: 10_000 }),
      draft({ kind: 'video', durationSeconds: null, totalBytes: 2_000_000 }),
    ]);
    const sampled = recordProgress(promote(state), itemIds[0], 1_000, 1);

    expect(getBatchEtaSeconds(sampled)).toBe((9_000 + 2_000_000) / 1_000);
  });

  it('stays numerically sound on files smaller than one multipart part and zero-time samples', () => {
    const { state, id } = uploadingState(500);

    const wholeFileAtOnce = recordProgress(state, id, 500, 0.5);
    expect(wholeFileAtOnce.bytesPerSecond).toBe(1_000);
    expect(getProgressRatio(item(wholeFileAtOnce, id))).toBe(1);

    const zeroDelta = recordProgress(state, id, 300, 0);
    expect(item(zeroDelta, id).sentBytes).toBe(300);
    expect(zeroDelta.bytesPerSecond).toBeNull();
    expect(getBatchEtaSeconds(zeroDelta)).toBeNull();
  });

  function transcodingVideo(durationSeconds: number | null): { state: UploadState; id: number } {
    const { state } = enqueue(createInitialState(), [
      draft({ kind: 'video', durationSeconds, totalBytes: 50_000_000 }),
    ]);
    const running = promote(state);
    return { state: running, id: getTranscodingItems(running)[0].id };
  }

  it('measures transcoding speed from ffmpeg progress and smooths new samples toward it', () => {
    const { state, id } = transcodingVideo(100);

    const first = recordTranscodeProgress(state, id, 0.1, 1);
    expect(first.transcodeSecondsPerSecond).toBe(10);

    const second = recordTranscodeProgress(first, id, 0.3, 1);
    expect(second.transcodeSecondsPerSecond).toBeGreaterThan(10);
    expect(second.transcodeSecondsPerSecond).toBeLessThan(20);
    expect(item(second, id).transcodeRatio).toBe(0.3);
  });

  it('shows the remaining transcoding time in the ETA before any byte is uploaded', () => {
    const { state, id } = transcodingVideo(100);

    const sampled = recordTranscodeProgress(state, id, 0.1, 1);

    expect(getBatchEtaSeconds(sampled)).toBe(((1 - 0.1) * 100) / 10);
  });

  it('sums transcoding and upload time once both lanes have a measured rate', () => {
    const { state, itemIds } = enqueueWithMeetings(createInitialState(), [
      draft({ durationSeconds: 10, totalBytes: 10_000 }),
      draft({ kind: 'video', durationSeconds: 100, totalBytes: 50_000_000 }),
    ]);
    const running = promote(state);
    const [audioId, videoId] = itemIds;

    const withUpload = recordProgress(running, audioId, 1_000, 1);
    const withTranscode = recordTranscodeProgress(withUpload, videoId, 0.2, 1);

    const uploadSeconds = (9_000 + 100 * ESTIMATED_MP3_BYTES_PER_SECOND) / 1_000;
    const transcodeSeconds = ((1 - 0.2) * 100) / 20;
    expect(getBatchEtaSeconds(withTranscode)).toBe(uploadSeconds + transcodeSeconds);
  });

  it('cannot measure transcoding speed for a video whose duration is unknown', () => {
    const { state, id } = transcodingVideo(null);

    const sampled = recordTranscodeProgress(state, id, 0.5, 1);

    expect(sampled.transcodeSecondsPerSecond).toBeNull();
    expect(item(sampled, id).transcodeRatio).toBe(0.5);
    expect(getBatchEtaSeconds(sampled)).toBeNull();
  });

  it('reports per-file progress as the ratio of bytes really sent', () => {
    const { state, id } = uploadingState(10_000);
    expect(getProgressRatio(item(state, id))).toBe(0);

    const halfway = recordProgress(state, id, 5_000, 1);
    expect(getProgressRatio(item(halfway, id))).toBe(0.5);

    const empty = item(
      promote(enqueueWithMeetings(createInitialState(), [draft({ totalBytes: 0 })]).state),
      1,
    );
    expect(getProgressRatio(empty)).toBe(0);
  });
});

describe('upload-batch aggregate title, flags and error messages', () => {
  it('titles the work in progress by its size, then announces the outcome exactly when the last file settles', () => {
    expect(getBatchTitle(createInitialState())).toBeNull();

    const { state, itemIds } = enqueueWithMeetings(createInitialState(), [
      draft({ durationSeconds: 10 }),
      draft({ durationSeconds: 20 }),
      draft({ durationSeconds: 30 }),
    ]);
    expect(getBatchTitle(state)).toEqual({
      key: 'meeting.import.batch.title-active',
      params: { count: 3 },
    });

    const twoSettled = fail(complete(state, itemIds[0]), itemIds[1], 'timeout');
    expect(getBatchTitle(twoSettled)).toEqual({
      key: 'meeting.import.batch.title-active',
      params: { count: 3 },
    });

    const allSettled = complete(twoSettled, itemIds[2]);
    expect(getBatchTitle(allSettled)).toEqual({
      key: 'meeting.import.batch.title-settled-with-errors',
      params: { success: 2, failed: 1 },
    });
  });

  it('announces a fully successful batch without mentioning errors', () => {
    const { state, itemIds } = enqueue(createInitialState(), [draft(), draft()]);
    const allDone = complete(complete(state, itemIds[0]), itemIds[1]);

    expect(getBatchTitle(allDone)).toEqual({
      key: 'meeting.import.batch.title-settled',
      params: { success: 2 },
    });
  });

  it('reports active work while at least one file is unsettled, and settlement only when all are', () => {
    expect(hasActiveWork(createInitialState())).toBe(false);
    expect(isSettled(createInitialState())).toBe(false);

    const { state, itemIds } = enqueue(createInitialState(), [draft(), draft()]);
    const oneSettled = complete(state, itemIds[0]);
    expect(hasActiveWork(oneSettled)).toBe(true);
    expect(isSettled(oneSettled)).toBe(false);

    const bothSettled = fail(oneSettled, itemIds[1], 'offline');
    expect(hasActiveWork(bothSettled)).toBe(false);
    expect(isSettled(bothSettled)).toBe(true);
  });

  it('recognises the sole item of the store, and stops as soon as another joins it', () => {
    const { state, itemIds } = enqueue(createInitialState(), [draft()]);
    expect(isSoleItem(state, itemIds[0])).toBe(true);

    const { state: withSecond } = enqueue(state, [draft()]);
    expect(isSoleItem(withSecond, itemIds[0])).toBe(false);

    expect(isSoleItem(createInitialState(), itemIds[0])).toBe(false);
  });

  it.each([
    ['offline', 'meeting.import.errors.connection'],
    ['blocked', 'meeting.import.errors.connection'],
    ['timeout', 'meeting.import.errors.server'],
    ['http-server', 'meeting.import.errors.server'],
    ['unknown', 'meeting.import.errors.server'],
    ['http-client', 'meeting.import.errors.file-unprocessable'],
  ] as const)('maps a %s failure to its user message', (failureType, expectedKey) => {
    const { state, itemIds } = enqueue(createInitialState(), [draft()]);
    const errored = fail(state, itemIds[0], failureType);

    expect(getFailureMessageKey(item(errored, itemIds[0]))).toBe(expectedKey);
  });

  it('gives no error message for a file that has not failed', () => {
    const { state, itemIds } = enqueue(createInitialState(), [draft()]);

    expect(getFailureMessageKey(item(state, itemIds[0]))).toBeNull();
    expect(getFailureMessageKey(item(complete(state, itemIds[0]), itemIds[0]))).toBeNull();
  });
});
