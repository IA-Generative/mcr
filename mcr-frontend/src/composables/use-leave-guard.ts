import type { ComputedRef } from 'vue';

type UseLeaveGuardOptions = {
  isInactive: ComputedRef<boolean>;
  confirm: () => Promise<boolean>;
};

export function useLeaveGuard({ isInactive, confirm }: UseLeaveGuardOptions) {
  function beforeUnloadHandler(e: BeforeUnloadEvent) {
    e.preventDefault();
    e.returnValue = true;
  }

  onMounted(() => {
    window.addEventListener('beforeunload', beforeUnloadHandler);
  });

  onUnmounted(() => {
    window.removeEventListener('beforeunload', beforeUnloadHandler);
  });

  onBeforeRouteLeave(async () => {
    return isInactive.value || (await confirm());
  });
}
