import { useAudioChunkStore } from './use-audio-chunk-store';

export const STALE_CHUNKS_MAX_AGE_MS = 24 * 60 * 60 * 1000; // 24h

export function useAudioChunkCleanup() {
  const { deleteAllChunksForMeeting, deleteStaleChunks } = useAudioChunkStore();

  function cleanupMeetingChunks(meetingId: number) {
    deleteAllChunksForMeeting(meetingId).catch(console.error);
  }

  function cleanupStaleChunks() {
    deleteStaleChunks(STALE_CHUNKS_MAX_AGE_MS).catch(console.error);
  }

  return { cleanupMeetingChunks, cleanupStaleChunks };
}
