import BaseModal from '@/components/core/BaseModal.vue';
import { useUploadBatch, useUploadBatchWriter } from '@/composables/use-upload-batch';
import { useUploadStatus } from '@/composables/use-upload-status';
import { t } from '@/plugins/i18n';
import { requestMeetingRemovalDuringUnload } from '@/services/meetings/meetings.service';
import { useModal } from 'vue-final-modal';

let isConfirming = false;

export type ConfirmDialog = { title: string; text: string; ctaLabel: string };

export function dialogFor(namespace: string): ConfirmDialog {
  return {
    title: t(`${namespace}.title`),
    text: t(`${namespace}.description`),
    ctaLabel: t(`${namespace}.button`),
  };
}

export async function confirmAbortActiveUploads(
  dialog: ConfirmDialog,
  { leavingPage = false } = {},
): Promise<boolean> {
  const { hasActiveWork } = useUploadBatch();
  const { abortActiveUploads } = useUploadStatus();
  const { clearAll } = useUploadBatchWriter();

  if (!hasActiveWork.value) {
    return true;
  }

  if (isConfirming) {
    return false;
  }

  isConfirming = true;
  try {
    const confirmed = await confirmLeave(dialog);
    if (confirmed) {
      if (leavingPage) {
        handOverCleanupToTheBrowser();
      }
      abortActiveUploads();
      clearAll();
    }

    return confirmed;
  } finally {
    isConfirming = false;
  }
}

function handOverCleanupToTheBrowser(): void {
  const { pendingMeetingIds } = useUploadBatch();
  const { clearAll } = useUploadBatchWriter();

  requestMeetingRemovalDuringUnload(pendingMeetingIds.value);
  // Emptying the store before the abort matters: the abort callbacks read it
  // synchronously to delete the meetings themselves, and that request would be
  // cancelled by the unloading page. The keepalive request above owns it now.
  clearAll();
}

export function confirmLeaveIfUploading(): Promise<boolean> {
  return confirmAbortActiveUploads(dialogFor('meeting.import.confirm-leave'), {
    leavingPage: true,
  });
}

export function confirmLeave(dialog: ConfirmDialog): Promise<boolean> {
  return new Promise((resolve) => {
    let confirmed = false;
    const modal = useModal({
      component: BaseModal,
      attrs: {
        title: dialog.title,
        text: dialog.text,
        ctaLabel: dialog.ctaLabel,
        onSuccess: () => {
          confirmed = true;
        },
        onClosed: () => {
          resolve(confirmed);
          modal.destroy();
        },
      },
    });
    void modal.open();
  });
}
