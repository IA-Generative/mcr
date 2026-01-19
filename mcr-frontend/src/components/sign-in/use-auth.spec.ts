import { describe, it, expect, vi, beforeEach } from 'vitest';
import { nextTick } from 'vue';
import { useAuth } from './use-auth';
import { ROUTES } from '@/router/routes';
import {
  createAuthMocks,
  setupErrorMocks,
  triggerError,
  type MockAuthDependencies,
} from './use-auth.test-utils';

vi.mock('@/composables/use-toaster');
vi.mock('@/services/auth/auth.service');
vi.mock('@/services/http/http.service');
vi.mock('@/stores/useUserStore');
vi.mock('@dsb-norge/vue-keycloak-js');
vi.mock('vue-i18n');
vi.mock('vue-router');
vi.mock('@tanstack/vue-query');

vi.mock('@/services/http/http.utils', () => ({
  is401Error: vi.fn(),
  is403Error: vi.fn(),
}));

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

  describe('test_handle_auth_error_should_redirect_to_not_tester_when_401_error_occurs', () => {
    it('should redirect to NOT_TESTER when 401 error occurs', async () => {
      setupErrorMocks(true, true, false);
      triggerError(mocks, new Error('Unauthorized'), useAuth);
      await nextTick();

      expect(mocks.router.push).toHaveBeenCalledWith(ROUTES.NOT_TESTER.path);
      expect(mocks.toaster.addErrorMessage).toHaveBeenCalledWith('error.default');
      expect(mocks.userStore.setUser).toHaveBeenCalledWith(null);
    });
  });

  describe('test_handle_auth_error_should_redirect_to_not_tester_when_403_error_occurs', () => {
    it('should redirect to NOT_TESTER when 403 error occurs', async () => {
      setupErrorMocks(true, false, true);
      triggerError(mocks, new Error('Forbidden'), useAuth);
      await nextTick();

      expect(mocks.router.push).toHaveBeenCalledWith(ROUTES.NOT_TESTER.path);
      expect(mocks.toaster.addErrorMessage).toHaveBeenCalledWith('error.default');
      expect(mocks.userStore.setUser).toHaveBeenCalledWith(null);
    });
  });

  describe('test_handle_auth_error_should_redirect_to_login_error_when_other_axios_error_occurs', () => {
    it('should redirect to LOGIN_ERROR when other Axios error occurs', async () => {
      setupErrorMocks(true, false, false);
      triggerError(mocks, new Error('Internal Server Error'), useAuth);
      await nextTick();

      expect(mocks.router.push).toHaveBeenCalledWith(ROUTES.LOGIN_ERROR.path);
      expect(mocks.toaster.addErrorMessage).toHaveBeenCalledWith('error.default');
      expect(mocks.userStore.setUser).not.toHaveBeenCalled();
    });
  });

  describe('test_handle_auth_error_should_redirect_to_login_error_when_non_axios_error_occurs', () => {
    it('should redirect to LOGIN_ERROR when non-Axios error occurs', async () => {
      setupErrorMocks(false, false, false);
      triggerError(mocks, new Error('Generic Error'), useAuth);
      await nextTick();

      expect(mocks.router.push).toHaveBeenCalledWith(ROUTES.LOGIN_ERROR.path);
      expect(mocks.toaster.addErrorMessage).toHaveBeenCalledWith('error.default');
      expect(mocks.userStore.setUser).not.toHaveBeenCalled();
    });
  });

  describe('test_handle_auth_error_should_not_redirect_when_no_error', () => {
    it('should not redirect when no error occurs', async () => {
      triggerError(mocks, null, useAuth);
      await nextTick();

      expect(mocks.router.push).not.toHaveBeenCalled();
      expect(mocks.toaster.addErrorMessage).not.toHaveBeenCalled();
      expect(mocks.userStore.setUser).not.toHaveBeenCalled();
    });
  });
});
