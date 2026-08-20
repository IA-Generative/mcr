import BaseModal from '@/components/core/BaseModal.vue';
import { useUploadBatch, useUploadBatchWriter } from '@/composables/use-upload-batch';
import { useImportRuntimes } from '@/composables/use-import-runtimes';
import { useUploadStatus } from '@/composables/use-upload-status';
import { t } from '@/plugins/i18n';
import { removeMany } from '@/services/meetings/meetings.service';
import { reportError } from '@/services/observability/sentry';
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
  const { forgetAll } = useImportRuntimes();
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
      const abandonedMeetingIds = leavingPage ? standAppDown() : [];
      abortActiveUploads();
      forgetAll();
      clearAll();
      await deleteAbandonedMeetings(abandonedMeetingIds);
    }

    return confirmed;
  } finally {
    isConfirming = false;
  }
}

function standAppDown(): number[] {
  const { pendingMeetingIds } = useUploadBatch();
  const { clearAll } = useUploadBatchWriter();

  const abandoned = [...pendingMeetingIds.value];
  // Emptying the store before the abort matters: the abort callbacks read it
  // synchronously and would queue a second delete for the very meetings this
  // flow deletes itself below.
  clearAll();
  return abandoned;
}

async function deleteAbandonedMeetings(meetingIds: number[]): Promise<void> {
  if (meetingIds.length === 0) {
    return;
  }

  // Signing out is never blocked by a failed cleanup: the meetings simply stay.
  try {
    await removeMany(meetingIds);
  } catch (error) {
    reportError(error, {
      feature: 'meeting.import',
      tags: { 'import.phase': 'sign-out-cleanup' },
      contexts: { import: { meetingIds } },
    });
  }
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
