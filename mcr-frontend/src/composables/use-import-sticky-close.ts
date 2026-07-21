import { confirmAbortActiveUploads, dialogFor } from '@/composables/use-confirm-leave';
import { useUploadBatch, useUploadBatchWriter } from '@/composables/use-upload-batch';

export function useImportStickyClose() {
  const { hasActiveWork } = useUploadBatch();
  const { clearAll } = useUploadBatchWriter();

  async function close(): Promise<void> {
    if (!hasActiveWork.value) {
      clearAll();
      return;
    }

    await confirmAbortActiveUploads(dialogFor('meeting.import.confirm-close'));
  }

  return { close };
}
