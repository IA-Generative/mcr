import { vi } from 'vitest';
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import useToaster from '@/composables/use-toaster';
import { useQuery, useQueryClient } from '@tanstack/vue-query';
import { useI18n } from 'vue-i18n';
import { useKeycloak } from '@dsb-norge/vue-keycloak-js';

export type MockAuthDependencies = {
  router: { push: ReturnType<typeof vi.fn> };
  toaster: { addErrorMessage: ReturnType<typeof vi.fn> };
  queryClient: { setQueryData: ReturnType<typeof vi.fn> };
  currentUserQuery: { error: ReturnType<typeof ref>; data: ReturnType<typeof ref> };
};

export const createAuthMocks = (): MockAuthDependencies => {
  const mocks: MockAuthDependencies = {
    router: { push: vi.fn() },
    toaster: { addErrorMessage: vi.fn() },
    queryClient: { setQueryData: vi.fn() },
    currentUserQuery: { error: ref(null), data: ref(null) },
  };

  vi.mocked(useRouter).mockReturnValue(mocks.router as any);
  vi.mocked(useToaster).mockReturnValue(mocks.toaster as any);
  vi.mocked(useQueryClient).mockReturnValue(mocks.queryClient as any);
  vi.mocked(useQuery).mockReturnValue(mocks.currentUserQuery as any);
  vi.mocked(useI18n).mockReturnValue({ t: vi.fn((key: string) => key) } as any);
  vi.mocked(useKeycloak).mockReturnValue({ keycloak: null } as any);

  return mocks;
};

export const triggerError = (
  mocks: MockAuthDependencies,
  error: Error | null,
  useAuth: () => any,
) => {
  useAuth();
  mocks.currentUserQuery.error.value = error;
};
