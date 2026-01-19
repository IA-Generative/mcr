import type { DsfrButtonProps } from '@gouvminint/vue-dsfr';
import { useI18n } from 'vue-i18n';

export type UseConfirmModalParams = {
  onClick: (value: boolean) => void;
};
export function useConfirmModal(params?: UseConfirmModalParams) {
  const { t } = useI18n();

  const title = t('common.modal.confirm-title.default');
  const opened = ref(false);

  const actions: DsfrButtonProps[] = [
    {
      label: t('common.yes'),
      onClick() {
        if (!params) {
          return;
        }
        params.onClick(true);
      },
    },
    {
      label: t('common.cancel'),
      onClick() {
        if (!params) {
          return;
        }
        params.onClick(false);
      },
      tertiary: true,
      noOutline: true,
    },
  ];

  function open() {
    opened.value = true;
  }

  function close() {
    opened.value = false;
  }

  return {
    title,
    actions,
    opened,
    open,
    close,
  };
}
