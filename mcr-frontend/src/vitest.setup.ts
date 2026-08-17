import { i18n } from '@/plugins/i18n';
import '@testing-library/jest-dom/vitest';
import { render, type RenderOptions } from '@testing-library/vue';
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query';
import { createPinia, getActivePinia, setActivePinia } from 'pinia';
import { ref } from 'vue';
import { beforeEach, vi } from 'vitest';

// Runs before any spec-level beforeEach, so a spec that activates its own pinia keeps it and
// renderWithPlugins installs that very instance — one store, whether the spec declared it or not.
beforeEach(() => {
  setActivePinia(undefined);
});

export function renderWithPlugins<C>(component: C, options: RenderOptions<C> = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const pinia = getActivePinia() ?? createPinia();
  setActivePinia(pinia);
  return render(component, {
    ...options,
    global: {
      ...options.global,
      plugins: [i18n, [VueQueryPlugin, { queryClient }], pinia, ...(options.global?.plugins ?? [])],
    },
  });
}

// Default return shape that satisfies both useQuery and useMutation consumers.
// Destructuring only picks the fields a caller asks for, so a single union-shape
// avoids having to detect query vs mutation by name.
const defaultUseMeetingFn = () => ({
  // Query fields
  data: ref(undefined),
  error: ref(null),
  isLoading: ref(false),
  isFetching: ref(false),
  refetch: vi.fn(),
  // Mutation fields
  mutate: vi.fn(),
  mutateAsync: vi.fn(),
  isPending: ref(false),
  reset: vi.fn(),
});

export function mockUseMeetings(overrides: Record<string, unknown> = {}) {
  return {
    useMeetings: () =>
      new Proxy(overrides, {
        get: (target, prop) => (prop in target ? target[prop as string] : defaultUseMeetingFn),
      }),
  };
}

// Mock ResizeObserver for testing environment
vi.stubGlobal(
  'ResizeObserver',
  class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  },
);
