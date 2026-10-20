import 'fake-indexeddb/auto';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAudioChunkStore, _resetDb } from './use-audio-chunk-store';

const { mockUploadFile, mockStartTranscription } = vi.hoisted(() => ({
  mockUploadFile: vi.fn(),
  mockStartTranscription: vi.fn(),
}));

vi.mock('@/services/meetings/use-meeting', () => ({
  useMeetings: () => ({
    uploadFileWithPresignedUrlMutation: () => ({
      mutateAsync: mockUploadFile,
    }),
    startTranscriptionMutation: () => ({
      mutateAsync: mockStartTranscription,
    }),
  }),
}));

vi.mock('@sentry/vue', () => ({
  logger: {
    error: vi.fn(),
    fmt: (strings: TemplateStringsArray, ...values: unknown[]) =>
      strings.reduce((acc, str, i) => acc + str + (values[i] ?? ''), ''),
  },
}));

describe('useChunkRecovery', () => {
  const store = useAudioChunkStore();
  const meetingId = 25399;

  beforeEach(async () => {
    vi.clearAllMocks();
    mockUploadFile.mockResolvedValue(undefined);
    mockStartTranscription.mockResolvedValue(undefined);
    await _resetDb();
    const { deleteDB } = await import('idb');
    await deleteDB('mcr-audio-chunks');
  });

  async function getComposable() {
    const { useChunkRecovery } = await import('./use-chunk-recovery');
    return useChunkRecovery(meetingId);
  }

  function makeBlob(content = 'audio') {
    return new Blob([content], { type: 'audio/weba' });
  }

  async function addPendingChunks(count: number) {
    for (let i = 0; i < count; i += 1) {
      await store.addChunk({ meetingId, filename: `${i}.weba`, blob: makeBlob() });
    }
  }

  it('sends the chunks left behind and hands the meeting to the transcription', async () => {
    await addPendingChunks(9);

    const { recoverPendingChunks } = await getComposable();
    const recovered = await recoverPendingChunks();

    expect(recovered).toBe(true);
    expect(mockUploadFile).toHaveBeenCalledTimes(9);
    expect(mockStartTranscription).toHaveBeenCalledWith(meetingId);
  });

  it('never starts the transcription while a chunk is still missing', async () => {
    await addPendingChunks(2);
    mockUploadFile.mockRejectedValueOnce(new Error('network error'));

    const { recoverPendingChunks } = await getComposable();
    const recovered = await recoverPendingChunks();

    expect(recovered).toBe(false);
    expect(mockStartTranscription).not.toHaveBeenCalled();
  });

  it('keeps the local copy when a chunk is still missing', async () => {
    await addPendingChunks(2);
    mockUploadFile.mockRejectedValueOnce(new Error('network error'));

    const { recoverPendingChunks } = await getComposable();
    await recoverPendingChunks();

    expect(await store.getChunkCountForMeeting(meetingId)).toBe(2);
  });

  it('drops the local copy once the transcription accepted the meeting', async () => {
    await addPendingChunks(3);

    const { recoverPendingChunks } = await getComposable();
    await recoverPendingChunks();

    expect(await store.getChunkCountForMeeting(meetingId)).toBe(0);
  });

  it('keeps the local copy when the transcription refuses the meeting', async () => {
    await addPendingChunks(3);
    mockStartTranscription.mockRejectedValueOnce(new Error('409'));

    const { recoverPendingChunks } = await getComposable();
    const recovered = await recoverPendingChunks();

    expect(recovered).toBe(false);
    expect(await store.getChunkCountForMeeting(meetingId)).toBe(3);
  });

  it('reports how many chunks are waiting so the page can offer the recovery', async () => {
    await addPendingChunks(9);

    const { pendingCount, refreshPendingCount } = await getComposable();
    await refreshPendingCount();

    expect(pendingCount.value).toBe(9);
  });

  it('reports nothing waiting once every chunk reached the server', async () => {
    await addPendingChunks(2);

    const { pendingCount, recoverPendingChunks } = await getComposable();
    await recoverPendingChunks();

    expect(pendingCount.value).toBe(0);
  });

  it('does not call the transcription when nothing is waiting', async () => {
    const { recoverPendingChunks } = await getComposable();
    const recovered = await recoverPendingChunks();

    expect(recovered).toBe(false);
    expect(mockUploadFile).not.toHaveBeenCalled();
    expect(mockStartTranscription).not.toHaveBeenCalled();
  });

  it('uploads each chunk once when the user clicks recover twice', async () => {
    await addPendingChunks(4);

    const { recoverPendingChunks } = await getComposable();
    await Promise.all([recoverPendingChunks(), recoverPendingChunks()]);

    expect(mockUploadFile).toHaveBeenCalledTimes(4);
    expect(mockStartTranscription).toHaveBeenCalledTimes(1);
  });

  it('ignores chunks belonging to another meeting', async () => {
    await addPendingChunks(2);
    await store.addChunk({ meetingId: 999, filename: 'other.weba', blob: makeBlob() });

    const { recoverPendingChunks } = await getComposable();
    await recoverPendingChunks();

    expect(mockUploadFile).toHaveBeenCalledTimes(2);
    expect(await store.getChunkCountForMeeting(999)).toBe(1);
  });
});
