import { ref } from 'vue';
import { useAudioChunkStore } from '@/composables/use-audio-chunk-store';
import { useChunkUpload } from '@/composables/use-chunk-upload';
import { useMeetings } from '@/services/meetings/use-meeting';
import * as Sentry from '@sentry/vue';

export function useChunkRecovery(meetingId: number) {
  const { getPendingChunksForMeeting, deleteAllChunksForMeeting } = useAudioChunkStore();
  const { uploadPendingFromIdb } = useChunkUpload(meetingId);
  const { startTranscriptionMutation } = useMeetings();
  const { mutateAsync: startTranscription } = startTranscriptionMutation();

  const pendingCount = ref(0);
  const isRecovering = ref(false);

  async function countPendingChunks(): Promise<number> {
    const pending = await getPendingChunksForMeeting(meetingId).catch(() => []);
    return pending.length;
  }

  async function refreshPendingCount(): Promise<number> {
    pendingCount.value = await countPendingChunks();
    return pendingCount.value;
  }

  async function recoverPendingChunks(): Promise<boolean> {
    if (isRecovering.value) return false;
    isRecovering.value = true;
    try {
      if ((await refreshPendingCount()) === 0) return false;

      await uploadPendingFromIdb();
      if ((await refreshPendingCount()) > 0) return false;

      await startTranscription(meetingId);
      await deleteAllChunksForMeeting(meetingId);
      return true;
    } catch (error) {
      Sentry.logger.error(
        Sentry.logger.fmt`Meeting ${meetingId} - chunk recovery failed - ${error}`,
      );
      return false;
    } finally {
      isRecovering.value = false;
    }
  }

  return { pendingCount, isRecovering, refreshPendingCount, recoverPendingChunks };
}
