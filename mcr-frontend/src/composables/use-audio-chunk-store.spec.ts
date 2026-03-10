import 'fake-indexeddb/auto';
import { describe, it, expect, beforeEach } from 'vitest';
import { useAudioChunkStore, _resetDb } from './use-audio-chunk-store';

const store = useAudioChunkStore();

beforeEach(async () => {
  await _resetDb();
  const { deleteDB } = await import('idb');
  await deleteDB('mcr-audio-chunks');
});

function createFakeChunk(meetingId: number, filename = 'test.weba') {
  return {
    meetingId,
    filename,
    blob: new Blob(['fake-audio-data'], { type: 'audio/weba' }),
  };
}

async function findChunkById(meetingId: number, chunkId: number) {
  const pendingChunks = await store.getPendingChunksForMeeting(meetingId);
  const chunk = pendingChunks.find((c) => c.id === chunkId);

  return chunk;
}

describe('useAudioChunkStore', () => {
  describe('addChunk', () => {
    it('returns a numeric id', async () => {
      const chunkId = await store.addChunk(createFakeChunk(1));
      expect(typeof chunkId).toBe('number');
    });

    it('auto-sets status to pending', async () => {
      const chunkId = await store.addChunk(createFakeChunk(1));
      const chunk = await findChunkById(1, chunkId);
      expect(chunk?.status).toBe('pending');
    });

    it('auto-sets createdAt to current timestamp', async () => {
      const before = Date.now();
      const chunkId = await store.addChunk(createFakeChunk(1));
      const after = Date.now();
      const chunk = await findChunkById(1, chunkId);
      expect(chunk?.createdAt).toBeGreaterThanOrEqual(before);
      expect(chunk?.createdAt).toBeLessThanOrEqual(after);
    });

    it('stores the blob and filename correctly', async () => {
      const chunkId = await store.addChunk(createFakeChunk(1, '12345.weba'));
      const chunk = await findChunkById(1, chunkId);
      expect(chunk?.filename).toBe('12345.weba');
      expect(chunk?.blob).toBeDefined();
    });
  });

  describe('markChunkUploaded', () => {
    it('transitions status from pending to uploaded', async () => {
      const chunkId = await store.addChunk(createFakeChunk(1));
      await store.markChunkUploaded(chunkId);
      const chunk = await findChunkById(1, chunkId);
      expect(chunk).toBeUndefined();
    });

    it('does not throw if chunk does not exist', async () => {
      await expect(store.markChunkUploaded(99999)).resolves.toBeUndefined();
    });
  });

  describe('getPendingChunksForMeeting', () => {
    it('returns only pending chunks for the given meetingId', async () => {
      await store.addChunk(createFakeChunk(1, 'a.weba'));
      await store.addChunk(createFakeChunk(1, 'b.weba'));
      const pending = await store.getPendingChunksForMeeting(1);
      expect(pending).toHaveLength(2);
      expect(pending.every((c) => c.meetingId === 1)).toBe(true);
    });

    it('excludes uploaded chunks', async () => {
      const id = await store.addChunk(createFakeChunk(1));
      await store.markChunkUploaded(id);
      const pending = await store.getPendingChunksForMeeting(1);
      expect(pending).toHaveLength(0);
    });

    it('excludes chunks from other meetings', async () => {
      await store.addChunk(createFakeChunk(1));
      await store.addChunk(createFakeChunk(2));
      const pending = await store.getPendingChunksForMeeting(1);
      expect(pending).toHaveLength(1);
      expect(pending[0].meetingId).toBe(1);
    });

    it('returns empty array when no pending chunks exist', async () => {
      const pending = await store.getPendingChunksForMeeting(999);
      expect(pending).toEqual([]);
    });
  });

  describe('getChunkCountForMeeting', () => {
    it('counts both pending and uploaded chunks', async () => {
      const id = await store.addChunk(createFakeChunk(1));
      await store.addChunk(createFakeChunk(1));
      await store.markChunkUploaded(id);
      const count = await store.getChunkCountForMeeting(1);
      expect(count).toBe(2);
    });

    it('excludes chunks from other meetings', async () => {
      await store.addChunk(createFakeChunk(1));
      await store.addChunk(createFakeChunk(2));
      const count = await store.getChunkCountForMeeting(1);
      expect(count).toBe(1);
    });

    it('returns 0 when no chunks exist', async () => {
      const count = await store.getChunkCountForMeeting(999);
      expect(count).toBe(0);
    });
  });
});
