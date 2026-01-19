import { useI18n } from 'vue-i18n';

export function useTranslateError() {
  const { t } = useI18n();

  function translate(key?: string) {
    if (key) {
      return t(key);
    }
  }

  return {
    translate,
  };
}
