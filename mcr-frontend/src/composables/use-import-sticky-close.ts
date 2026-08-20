import { confirmAbortActiveUploads, dialogFor } from '@/composables/use-confirm-leave';
import { useImportRuntimes } from '@/composables/use-import-runtimes';
import { useUploadBatch, useUploadBatchWriter } from '@/composables/use-upload-batch';

export function useImportStickyClose() {
  const { hasActiveWork } = useUploadBatch();
  const { clearAll } = useUploadBatchWriter();
  const { forgetAll } = useImportRuntimes();

  async function close(): Promise<void> {
    if (!hasActiveWork.value) {
      forgetAll();
      clearAll();
      return;
    }

    await confirmAbortActiveUploads(dialogFor('meeting.import.confirm-close'));
  }

  return { close };
}
