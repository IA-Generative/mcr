import BaseModal from '@/components/core/BaseModal.vue';
import { t } from '@/plugins/i18n';
import { useModal } from 'vue-final-modal';

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
