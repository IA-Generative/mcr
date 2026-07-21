import BaseModal from '@/components/core/BaseModal.vue';
import { useUploadBatch, useUploadBatchWriter } from '@/composables/use-upload-batch';
import { useUploadStatus } from '@/composables/use-upload-status';
import { t } from '@/plugins/i18n';
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

export async function confirmAbortActiveUploads(dialog: ConfirmDialog): Promise<boolean> {
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
      abortActiveUploads();
      clearAll();
    }

    return confirmed;
  } finally {
    isConfirming = false;
  }
}

export function confirmLeaveIfUploading(): Promise<boolean> {
  return confirmAbortActiveUploads(dialogFor('meeting.import.confirm-leave'));
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
