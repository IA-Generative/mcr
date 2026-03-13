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
      const dateBeforeCreation = Date.now();
      const chunkId = await store.addChunk(createFakeChunk(1));
      const dateAfterCreation = Date.now();

      const chunk = await findChunkById(1, chunkId);
      expect(chunk?.createdAt).toBeGreaterThanOrEqual(dateBeforeCreation);
      expect(chunk?.createdAt).toBeLessThanOrEqual(dateAfterCreation);
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

  describe('deleteAllChunksForMeeting', () => {
    it('removes all chunks (pending + uploaded) for the meeting', async () => {
      const id = await store.addChunk(createFakeChunk(1));
      await store.addChunk(createFakeChunk(1));
      await store.markChunkUploaded(id);
      await store.deleteAllChunksForMeeting(1);
      const count = await store.getChunkCountForMeeting(1);
      expect(count).toBe(0);
    });

    it('does not affect chunks from other meetings', async () => {
      await store.addChunk(createFakeChunk(1));
      await store.addChunk(createFakeChunk(2));
      await store.deleteAllChunksForMeeting(1);
      const count = await store.getChunkCountForMeeting(2);
      expect(count).toBe(1);
    });
  });

  describe('deleteStaleChunks', () => {
    it('removes chunks older than maxAgeMs regardless of status', async () => {
      // Add chunks with old createdAt by directly manipulating via addChunk then updating
      const id1 = await store.addChunk(createFakeChunk(1));
      const id2 = await store.addChunk(createFakeChunk(1));
      await store.markChunkUploaded(id2);

      // Manually age the records by accessing IDB directly
      const { openDB } = await import('idb');
      const db = await openDB('mcr-audio-chunks', 1);
      const tx = db.transaction('audio-chunks', 'readwrite');
      for (const id of [id1, id2]) {
        const record = await tx.store.get(id);
        record.createdAt = Date.now() - 2 * 60 * 60 * 1000; // 2 hours ago
        await tx.store.put(record);
      }
      await tx.done;
      db.close();

      await store.deleteStaleChunks(1 * 60 * 60 * 1000); // 1 hour TTL
      const count = await store.getChunkCountForMeeting(1);
      expect(count).toBe(0);
    });

    it('keeps chunks newer than maxAgeMs', async () => {
      await store.addChunk(createFakeChunk(1));
      await store.deleteStaleChunks(1 * 60 * 60 * 1000); // 1 hour TTL
      const count = await store.getChunkCountForMeeting(1);
      expect(count).toBe(1);
    });

    it('works across multiple meetings', async () => {
      await store.addChunk(createFakeChunk(1));
      await store.addChunk(createFakeChunk(2));

      const { openDB } = await import('idb');
      const db = await openDB('mcr-audio-chunks', 1);
      const all = await db.getAll('audio-chunks');
      const tx = db.transaction('audio-chunks', 'readwrite');
      for (const record of all) {
        record.createdAt = Date.now() - 2 * 60 * 60 * 1000;
        await tx.store.put(record);
      }
      await tx.done;
      db.close();

      await store.deleteStaleChunks(1 * 60 * 60 * 1000);
      expect(await store.getChunkCountForMeeting(1)).toBe(0);
      expect(await store.getChunkCountForMeeting(2)).toBe(0);
    });
  });
});
