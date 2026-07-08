import type { ComputedRef } from 'vue';

export function useUnloadWarning(isActive: ComputedRef<boolean>) {
  function beforeUnloadHandler(e: BeforeUnloadEvent) {
    if (!isActive.value) {
      return;
    }

    e.preventDefault();
    e.returnValue = true;
  }

  onMounted(() => {
    window.addEventListener('beforeunload', beforeUnloadHandler);
  });

  onUnmounted(() => {
    window.removeEventListener('beforeunload', beforeUnloadHandler);
  });
}
