import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import { ROUTES } from '@/router/routes';

const routes: RouteRecordRaw[] = Object.values(ROUTES);

const router = () => {
  return createRouter({
    history: createWebHistory(import.meta.env?.BASE_URL || ''),
    routes,
  });
};

export default router;
