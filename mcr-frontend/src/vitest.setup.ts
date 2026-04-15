import { i18n } from '@/plugins/i18n';
import '@testing-library/jest-dom/vitest';
import { render, type RenderOptions } from '@testing-library/vue';
import { VueQueryPlugin } from '@tanstack/vue-query';
import { ref } from 'vue';
import { vi } from 'vitest';

export function renderWithPlugins<C>(component: C, options: RenderOptions<C> = {}) {
  return render(component, {
    ...options,
    global: {
      plugins: [i18n, VueQueryPlugin],
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
