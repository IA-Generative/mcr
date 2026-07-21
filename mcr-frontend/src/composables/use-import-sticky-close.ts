import { confirmLeave } from '@/composables/use-confirm-leave';
import { useUploadBatch, useUploadBatchWriter } from '@/composables/use-upload-batch';
import { useUploadStatus } from '@/composables/use-upload-status';
import { t } from '@/plugins/i18n';

let isClosing = false;

export function useImportStickyClose() {
  const { hasActiveWork } = useUploadBatch();
  const { clearAll } = useUploadBatchWriter();
  const { abortActiveUploads } = useUploadStatus();

  async function close(): Promise<void> {
    if (!hasActiveWork.value) {
      clearAll();
      return;
    }

    if (isClosing) {
      return;
    }

    isClosing = true;
    try {
      const confirmed = await confirmLeave({
        title: t('meeting.import.confirm-close.title'),
        text: t('meeting.import.confirm-close.description'),
        ctaLabel: t('meeting.import.confirm-close.button'),
      });
      if (confirmed) {
        abortActiveUploads();
        clearAll();
      }
    } finally {
      isClosing = false;
    }
  }

  return { close };
}
