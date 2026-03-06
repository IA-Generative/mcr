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

const defaultMutationFn = () => ({ mutate: vi.fn(), mutateAsync: vi.fn(), isPending: ref(false) });

export function mockUseMeetings(overrides: Record<string, unknown> = {}) {
  return {
    useMeetings: () =>
      new Proxy(overrides, {
        get: (target, prop) => (prop in target ? target[prop as string] : defaultMutationFn),
      }),
  };
}
