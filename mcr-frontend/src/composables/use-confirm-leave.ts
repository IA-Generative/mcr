import BaseModal from '@/components/core/BaseModal.vue';
import { useUploadStatus } from '@/composables/use-upload-status';
import { t } from '@/plugins/i18n';
import { useModal } from 'vue-final-modal';

let isConfirming = false;

/**
 * Single entry point shared by the router guard and the sign-out button: lets the
 * caller proceed when nothing is uploading, otherwise asks for confirmation and
 * aborts the uploads on an accepted leave. While the modal is open, any concurrent
 * caller (e.g. browser back/forward, which the modal overlay cannot block) is
 * denied instead of stacking a second modal.
 */
export async function confirmLeaveIfUploading(): Promise<boolean> {
  const { hasActiveUploads, abortActiveUploads } = useUploadStatus();
  if (!hasActiveUploads.value) return true;
  if (isConfirming) return false;

  isConfirming = true;
  try {
    const leave = await confirmLeave();
    if (leave) abortActiveUploads();
    return leave;
  } finally {
    isConfirming = false;
  }
}

/**
 * Opens the DSFR confirm-leave modal and resolves on EVERY close path (cancel,
 * ESC, outside click) — a pending promise here would deadlock the router guard
 * awaiting it.
 */
export function confirmLeave(): Promise<boolean> {
  return new Promise((resolve) => {
    let confirmed = false;
    const modal = useModal({
      component: BaseModal,
      attrs: {
        title: t('meeting.import.confirm-leave.title'),
        text: t('meeting.import.confirm-leave.description'),
        ctaLabel: t('meeting.import.confirm-leave.button'),
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
