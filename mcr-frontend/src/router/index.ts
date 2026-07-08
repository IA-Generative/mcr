import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import { ROUTES } from '@/router/routes';
import { useUnleash } from '@/composables/use-unleash';
import { uploadLeaveGuard } from '@/router/upload-leave-guard';

const routes: RouteRecordRaw[] = Object.values(ROUTES);

const router = () => {
  const instance = createRouter({
    history: createWebHistory(import.meta.env?.BASE_URL || ''),
    routes,
  });

  instance.beforeEach((to, from) => {
    const isMaintenanceEnabled = useUnleash().isEnabled('maintenance');
    if (isMaintenanceEnabled && to.name !== 'Maintenance') {
      return { name: 'Maintenance' };
    }
    if (!isMaintenanceEnabled && to.name === 'Maintenance') {
      return { name: 'MeetingList' };
    }

    const featureFlag = to.meta.featureFlag as string | undefined;
    if (featureFlag && !useUnleash().isEnabled(featureFlag)) {
      return { name: 'NotFound' };
    }

    return uploadLeaveGuard(to, from);
  });

  return instance;
};

export default router;
