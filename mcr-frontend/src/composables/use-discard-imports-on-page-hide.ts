import { useUploadBatch } from '@/composables/use-upload-batch';
import { requestMeetingRemovalDuringUnload } from '@/services/meetings/meetings.service';

export function useDiscardImportsOnPageHide(): void {
  const { pendingMeetingIds } = useUploadBatch();

  function discardPendingMeetings(): void {
    if (pendingMeetingIds.value.length === 0) {
      return;
    }

    requestMeetingRemovalDuringUnload(pendingMeetingIds.value);
  }

  onMounted(() => {
    window.addEventListener('pagehide', discardPendingMeetings);
  });

  onUnmounted(() => {
    window.removeEventListener('pagehide', discardPendingMeetings);
  });
}
