import { beforeEach, describe, expect, it, vi } from 'vitest';

const { keycloak, isInactive } = vi.hoisted(() => ({
  keycloak: {
    token: 'current-access-token',
    refreshTokenParsed: undefined as { exp?: number } | undefined,
    timeSkew: 0,
    updateToken: vi.fn(),
    login: vi.fn(),
  },
  isInactive: { value: true },
}));

vi.mock('@dsb-norge/vue-keycloak-js', () => ({
  useKeycloak: () => ({ keycloak }),
}));

vi.mock('@/composables/use-recorder', () => ({ isInactive }));

async function loadTokenProvider() {
  vi.resetModules();
  return await import('./token-provider');
}

function secondsFromNow(offset: number) {
  return Math.floor(Date.now() / 1000) + offset;
}

describe('getValidToken', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    isInactive.value = true;
    keycloak.token = 'current-access-token';
    keycloak.timeSkew = 0;
    keycloak.refreshTokenParsed = { exp: secondsFromNow(3600) };
    keycloak.updateToken.mockRejectedValue(new Error('Server responded with an invalid status.'));
  });

  it('reports a refresh the server refuses as an expired session, not as a transport failure', async () => {
    const { getValidToken, SessionExpiredError } = await loadTokenProvider();

    await expect(getValidToken()).rejects.toBeInstanceOf(SessionExpiredError);
  });

  it('sends the user back to the SSO when the server refuses the refresh', async () => {
    const { getValidToken } = await loadTokenProvider();

    await expect(getValidToken()).rejects.toThrow();

    expect(keycloak.login).toHaveBeenCalledTimes(1);
  });

  it('keeps a running recording on the page when the server refuses the refresh', async () => {
    const { getValidToken } = await loadTokenProvider();
    isInactive.value = false;

    await expect(getValidToken()).rejects.toThrow();

    expect(keycloak.login).not.toHaveBeenCalled();
  });

  it('returns the refreshed token while the server still honours the session', async () => {
    const { getValidToken } = await loadTokenProvider();
    keycloak.updateToken.mockResolvedValue(true);

    await expect(getValidToken()).resolves.toBe('current-access-token');
  });
});
