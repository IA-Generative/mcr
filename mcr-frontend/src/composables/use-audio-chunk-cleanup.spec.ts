import 'fake-indexeddb/auto';
import { describe, it, expect, beforeEach } from 'vitest';
import { useAudioChunkStore, _resetDb } from './use-audio-chunk-store';
import { useAudioChunkCleanup, STALE_CHUNKS_MAX_AGE_MS } from './use-audio-chunk-cleanup';

describe('useAudioChunkCleanup', () => {
  const store = useAudioChunkStore();

  beforeEach(async () => {
    await _resetDb();
    const { deleteDB } = await import('idb');
    await deleteDB('mcr-audio-chunks');
  });

  describe('cleanupMeetingChunks', () => {
    it('deletes all chunks for the given meetingId', async () => {
      const meetingId = 10;
      await store.addChunk({
        meetingId,
        filename: 'a.weba',
        blob: new Blob(['data']),
      });
      await store.addChunk({
        meetingId,
        filename: 'b.weba',
        blob: new Blob(['data']),
      });

      expect(await store.getChunkCountForMeeting(meetingId)).toBe(2);

      const { cleanupMeetingChunks } = useAudioChunkCleanup();
      cleanupMeetingChunks(meetingId);
      await new Promise((r) => setTimeout(r, 50));

      expect(await store.getChunkCountForMeeting(meetingId)).toBe(0);
    });

    it('does not throw if deleteAllChunksForMeeting fails', async () => {
      const { cleanupMeetingChunks } = useAudioChunkCleanup();
      cleanupMeetingChunks(99999);
      await new Promise((r) => setTimeout(r, 50));
      // No assertion needed — if it throws, the test fails
    });
  });

  describe('cleanupStaleChunks', () => {
    it('deletes chunks older than STALE_CHUNKS_MAX_AGE_MS', async () => {
      // Add chunks via the store (creates the DB with the correct schema)
      await store.addChunk({
        meetingId: 1,
        filename: 'recent.weba',
        blob: new Blob(['recent']),
      });
      const oldId = await store.addChunk({
        meetingId: 1,
        filename: 'old.weba',
        blob: new Blob(['old']),
      });

      // Manually backdate one chunk's createdAt via raw IDB access
      const { openDB } = await import('idb');
      const db = await openDB('mcr-audio-chunks', 1);
      const record = await db.get('audio-chunks', oldId);
      record.createdAt = Date.now() - STALE_CHUNKS_MAX_AGE_MS - 1000;
      await db.put('audio-chunks', record);
      db.close();
      await _resetDb();

      const { cleanupStaleChunks } = useAudioChunkCleanup();
      cleanupStaleChunks();
      await new Promise((r) => setTimeout(r, 50));

      expect(await store.getChunkCountForMeeting(1)).toBe(1);
    });
  });

  describe('STALE_CHUNKS_MAX_AGE_MS', () => {
    it('is 24 hours in milliseconds', () => {
      expect(STALE_CHUNKS_MAX_AGE_MS).toBe(24 * 60 * 60 * 1000);
    });
  });
});
