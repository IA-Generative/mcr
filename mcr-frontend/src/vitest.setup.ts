import { i18n } from '@/plugins/i18n';
import '@testing-library/jest-dom/vitest';
import { render, type RenderOptions } from '@testing-library/vue';
import { VueQueryPlugin } from '@tanstack/vue-query';

export function renderWithPlugins<C>(component: C, options: RenderOptions<C> = {}) {
  return render(component, {
    ...options,
    global: {
      plugins: [i18n, VueQueryPlugin],
    },
  });
}
