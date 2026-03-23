import { describe, it, expect, vi, beforeEach } from 'vitest';
import { nextTick } from 'vue';
import { useAuth } from './use-auth';
import { ROUTES } from '@/router/routes';
import { createAuthMocks, triggerError, type MockAuthDependencies } from './use-auth.test-utils';

vi.mock('@/composables/use-toaster');
vi.mock('@/services/auth/auth.service');
vi.mock('@/services/http/http.service');
vi.mock('@dsb-norge/vue-keycloak-js');
vi.mock('vue-i18n');
vi.mock('vue-router');
vi.mock('@tanstack/vue-query');

vi.mock('axios', () => {
  const create = vi.fn(() => ({
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
    defaults: { headers: { common: {} } },
  }));

  return {
    default: { create },
    isAxiosError: vi.fn(),
  };
});

vi.mock('@/router/routes', () => ({
  ROUTES: {
    NOT_TESTER: { path: '/non-tester' },
    LOGIN_ERROR: { path: '/login-error' },
  },
}));

describe("useAuth - Logique de routage d'erreur", () => {
  let mocks: MockAuthDependencies;

  beforeEach(() => {
    vi.clearAllMocks();
    mocks = createAuthMocks();
  });

  it('should redirect to LOGIN_ERROR when an error occurs', async () => {
    triggerError(mocks, new Error('Unauthorized'), useAuth);
    await nextTick();

    expect(mocks.router.push).toHaveBeenCalledWith(ROUTES.LOGIN_ERROR.path);
    expect(mocks.toaster.addErrorMessage).toHaveBeenCalledWith('error.default');
  });

  it('should redirect to LOGIN_ERROR when a generic error occurs', async () => {
    triggerError(mocks, new Error('Generic Error'), useAuth);
    await nextTick();

    expect(mocks.router.push).toHaveBeenCalledWith(ROUTES.LOGIN_ERROR.path);
    expect(mocks.toaster.addErrorMessage).toHaveBeenCalledWith('error.default');
  });

  it('should not redirect when no error occurs', async () => {
    triggerError(mocks, null, useAuth);
    await nextTick();

    expect(mocks.router.push).not.toHaveBeenCalled();
    expect(mocks.toaster.addErrorMessage).not.toHaveBeenCalled();
  });
});
