import { confirmLeave } from '@/composables/use-confirm-leave';
import { useUploadStatus } from '@/composables/use-upload-status';

export function createUploadLeaveGuard() {
  let isConfirming = false;

  return async (): Promise<boolean | undefined> => {
    const { hasActiveUploads, abortActiveUploads } = useUploadStatus();
    if (isConfirming) return false;
    if (!hasActiveUploads.value) return undefined;

    isConfirming = true;
    try {
      if (!(await confirmLeave())) return false;
    } finally {
      isConfirming = false;
    }

    abortActiveUploads();
    return undefined;
  };
}
