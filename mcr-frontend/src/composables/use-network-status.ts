export function useNetworkStatus() {
  const isOnline = ref(navigator.onLine);

  const onOnline = () => {
    isOnline.value = true;
  };
  const onOffline = () => {
    isOnline.value = false;
  };

  onMounted(() => {
    window.addEventListener('online', onOnline);
    window.addEventListener('offline', onOffline);
  });

  onUnmounted(() => {
    window.removeEventListener('online', onOnline);
    window.removeEventListener('offline', onOffline);
  });

  return { isOnline };
}
