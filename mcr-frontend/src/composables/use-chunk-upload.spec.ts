import 'fake-indexeddb/auto';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAudioChunkStore, _resetDb } from './use-audio-chunk-store';

const mockUploadFile = vi.fn();

vi.mock('@/services/meetings/use-meeting', () => ({
  useMeetings: () => ({
    uploadFileWithPresignedUrlMutation: () => ({
      mutateAsync: mockUploadFile,
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

describe('useChunkUpload', () => {
  const store = useAudioChunkStore();
  const meetingId = 42;

  beforeEach(async () => {
    vi.clearAllMocks();
    mockUploadFile.mockResolvedValue(undefined);
    await _resetDb();
    const { deleteDB } = await import('idb');
    await deleteDB('mcr-audio-chunks');
  });

  async function getComposable() {
    const { useChunkUpload } = await import('./use-chunk-upload');
    return useChunkUpload(meetingId);
  }

  function makeBlob(content = 'audio') {
    return new Blob([content], { type: 'audio/weba' });
  }

  describe('saveAndEnqueueUpload', () => {
    it('saves to IDB and uploads when online', async () => {
      const { saveAndEnqueueUpload, waitForAllUploads } = await getComposable();
      await saveAndEnqueueUpload(makeBlob(), 'test.weba', true);
      await waitForAllUploads();
      expect(mockUploadFile).toHaveBeenCalledTimes(1);
      const count = await store.getChunkCountForMeeting(meetingId);
      expect(count).toBe(1);
    });

    it('saves to IDB but does not upload when offline', async () => {
      const { saveAndEnqueueUpload, waitForAllUploads } = await getComposable();
      await saveAndEnqueueUpload(makeBlob(), 'test.weba', false);
      await waitForAllUploads();
      expect(mockUploadFile).not.toHaveBeenCalled();
      const pending = await store.getPendingChunksForMeeting(meetingId);
      expect(pending).toHaveLength(1);
    });

    it('marks chunk as uploaded on successful upload', async () => {
      const { saveAndEnqueueUpload, waitForAllUploads } = await getComposable();
      await saveAndEnqueueUpload(makeBlob(), 'test.weba', true);
      await waitForAllUploads();
      const pending = await store.getPendingChunksForMeeting(meetingId);
      expect(pending).toHaveLength(0);
    });

    it('does not throw when upload fails (error caught)', async () => {
      mockUploadFile.mockRejectedValueOnce(new Error('network error'));
      const { saveAndEnqueueUpload, waitForAllUploads } = await getComposable();
      await saveAndEnqueueUpload(makeBlob(), 'test.weba', true);
      await expect(waitForAllUploads()).resolves.toBeUndefined();
    });

    it('falls back to upload-only when IDB write fails', async () => {
      const addSpy = vi.spyOn(store, 'addChunk').mockRejectedValueOnce(new Error('quota'));
      const { saveAndEnqueueUpload, waitForAllUploads } = await getComposable();
      await saveAndEnqueueUpload(makeBlob(), 'test.weba', true);
      await waitForAllUploads();
      expect(mockUploadFile).toHaveBeenCalledTimes(1);
      addSpy.mockRestore();
    });
  });
  describe('waitForAllUploads', () => {
    it('resolves when all queued uploads complete', async () => {
      const { saveAndEnqueueUpload, waitForAllUploads } = await getComposable();
      await saveAndEnqueueUpload(makeBlob(), 'a.weba', true);
      await saveAndEnqueueUpload(makeBlob(), 'b.weba', true);
      await expect(waitForAllUploads()).resolves.toBeUndefined();
      expect(mockUploadFile).toHaveBeenCalledTimes(2);
    });

    it('resolves immediately when queue is empty', async () => {
      const { waitForAllUploads } = await getComposable();
      await expect(waitForAllUploads()).resolves.toBeUndefined();
    });
  });
});
