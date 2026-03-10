import { useAudioChunkStore } from './use-audio-chunk-store';
import { useMeetings } from '@/services/meetings/use-meeting';
import * as Sentry from '@sentry/vue';

export function useChunkUpload(meetingId: number) {
  const uploadQueue: Promise<void>[] = [];
  const uploadingChunkIds = new Set<number>();

  const { addChunk, markChunkUploaded } = useAudioChunkStore();
  const { uploadFileWithPresignedUrlMutation } = useMeetings();
  const { mutateAsync: uploadFile } = uploadFileWithPresignedUrlMutation();

  function isAlreadyUploading(chunkId: number | undefined | null): boolean {
    return chunkId !== null && chunkId !== undefined && uploadingChunkIds.has(chunkId);
  }

  async function doUpload(blob: Blob, filename: string, chunkId: number | null): Promise<void> {
    if (chunkId != null) uploadingChunkIds.add(chunkId);
    try {
      await uploadFile({
        meetingId,
        file: new File([blob], filename, { type: 'audio/weba' }),
      });
      if (chunkId != null) await markChunkUploaded(chunkId);
    } finally {
      if (chunkId != null) uploadingChunkIds.delete(chunkId);
    }
  }

  function enqueueUpload(blob: Blob, filename: string, chunkId: number | null) {
    if (isAlreadyUploading(chunkId)) return;
    const task = doUpload(blob, filename, chunkId).catch((error) => {
      Sentry.logger.error(
        Sentry.logger.fmt`Meeting ${meetingId} - chunk ${filename} - upload failed - ${error}`,
      );
    });
    uploadQueue.push(task);
  }

  async function saveAndEnqueueUpload(blob: Blob, filename: string, isOnline: boolean) {
    let chunkId: number | null = null;
    try {
      chunkId = await addChunk({ meetingId, filename, blob });
    } catch {
      /* IDB unavailable — continue without it */
    }
    if (isOnline) {
      enqueueUpload(blob, filename, chunkId);
    }
  }

  async function waitForAllUploads(): Promise<void> {
    await Promise.allSettled(uploadQueue);
  }

  return { saveAndEnqueueUpload, waitForAllUploads };
}
