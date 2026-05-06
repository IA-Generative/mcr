import { describe, it, expect, beforeEach } from 'vitest';
import { useSessionAlert } from './use-session-alert';

const SESSION_KEY = 'test-alert-key';

describe('useSessionAlert', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it('shows alert by default when sessionStorage is empty', () => {
    const { showAlert } = useSessionAlert(SESSION_KEY);
    expect(showAlert.value).toBe(true);
  });

  it('hides alert when sessionStorage already has the closed value', () => {
    sessionStorage.setItem(SESSION_KEY, 'CLOSED_ALERT');
    const { showAlert } = useSessionAlert(SESSION_KEY);
    expect(showAlert.value).toBe(false);
  });

  it('closeAlert hides alert and persists to sessionStorage', () => {
    const { showAlert, closeAlert } = useSessionAlert(SESSION_KEY);
    expect(showAlert.value).toBe(true);

    closeAlert();

    expect(showAlert.value).toBe(false);
    expect(sessionStorage.getItem(SESSION_KEY)).toBe('CLOSED_ALERT');
  });
});
