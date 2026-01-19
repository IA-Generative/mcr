import { vi } from 'vitest';
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import useToaster from '@/composables/use-toaster';
import { useUserStore } from '@/stores/useUserStore';
import { useQuery } from '@tanstack/vue-query';
import { useI18n } from 'vue-i18n';
import { useKeycloak } from '@dsb-norge/vue-keycloak-js';
import { isAxiosError } from 'axios';
import { is401Error, is403Error } from '@/services/http/http.utils';

export type MockAuthDependencies = {
  router: { push: ReturnType<typeof vi.fn> };
  toaster: { addErrorMessage: ReturnType<typeof vi.fn> };
  userStore: { setUser: ReturnType<typeof vi.fn> };
  currentUserQuery: { error: ReturnType<typeof ref>; data: ReturnType<typeof ref> };
};

export const createAuthMocks = (): MockAuthDependencies => {
  const mocks: MockAuthDependencies = {
    router: { push: vi.fn() },
    toaster: { addErrorMessage: vi.fn() },
    userStore: { setUser: vi.fn() },
    currentUserQuery: { error: ref(null), data: ref(null) },
  };

  vi.mocked(useRouter).mockReturnValue(mocks.router as any);
  vi.mocked(useToaster).mockReturnValue(mocks.toaster as any);
  vi.mocked(useUserStore).mockReturnValue(mocks.userStore as any);
  vi.mocked(useQuery).mockReturnValue(mocks.currentUserQuery as any);
  vi.mocked(useI18n).mockReturnValue({ t: vi.fn((key: string) => key) } as any);
  vi.mocked(useKeycloak).mockReturnValue({ keycloak: null } as any);

  return mocks;
};

export const setupErrorMocks = (isAxios: boolean, is401: boolean, is403: boolean) => {
  vi.mocked(isAxiosError).mockReturnValue(isAxios);
  vi.mocked(is401Error).mockReturnValue(is401);
  vi.mocked(is403Error).mockReturnValue(is403);
};

export const triggerError = (
  mocks: MockAuthDependencies,
  error: Error | null,
  useAuth: () => any,
) => {
  useAuth();
  mocks.currentUserQuery.error.value = error;
};
