import BaseModal from '@/components/core/BaseModal.vue';
import { useUploadStatus } from '@/composables/use-upload-status';
import { t } from '@/plugins/i18n';
import { useModal } from 'vue-final-modal';

let isConfirming = false;

export async function confirmLeaveIfUploading(): Promise<boolean> {
  const { hasActiveUploads, abortActiveUploads } = useUploadStatus();

  if (!hasActiveUploads.value) {
    return true;
  }

  if (isConfirming) {
    return false;
  }

  isConfirming = true;
  try {
    const leave = await confirmLeave({
      title: t('meeting.import.confirm-leave.title'),
      text: t('meeting.import.confirm-leave.description'),
      ctaLabel: t('meeting.import.confirm-leave.button'),
    });
    if (leave) {
      abortActiveUploads();
    }

    return leave;
  } finally {
    isConfirming = false;
  }
}

export type ConfirmDialog = { title: string; text: string; ctaLabel: string };

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
