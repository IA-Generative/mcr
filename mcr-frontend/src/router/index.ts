import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import { ROUTES } from '@/router/routes';
import { useUnleash } from '@/composables/use-unleash';

const routes: RouteRecordRaw[] = Object.values(ROUTES);

const router = () => {
  const instance = createRouter({
    history: createWebHistory(import.meta.env?.BASE_URL || ''),
    routes,
  });

  instance.beforeEach((to) => {
    const featureFlag = to.meta.featureFlag as string | undefined;
    if (featureFlag && !useUnleash().isEnabled(featureFlag)) {
      return { name: 'NotFound' };
    }
  });

  return instance;
};

export default router;
