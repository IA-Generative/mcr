import { onBeforeUnmount, ref } from 'vue';
import { useUnleash } from '@/composables/use-unleash';

export function useFeatureFlag(flagName: string) {
  const unleash = useUnleash();
  const isEnabled = ref(false);

  const refresh = () => {
    isEnabled.value = unleash.isEnabled(flagName);
  };

  if (unleash.isReady()) refresh();
  else unleash.on('ready', refresh);

  unleash.on('update', refresh);

  onBeforeUnmount(() => {
    unleash.off('ready', refresh);
    unleash.off('update', refresh);
  });

  return isEnabled;
}
