export function useSessionAlert(sessionKey: string) {
  const CLOSED_VALUE = 'CLOSED_ALERT';
  const showAlert = ref(sessionStorage.getItem(sessionKey) !== CLOSED_VALUE);

  function closeAlert() {
    showAlert.value = false;
    sessionStorage.setItem(sessionKey, CLOSED_VALUE);
  }

  return { showAlert, closeAlert };
}
