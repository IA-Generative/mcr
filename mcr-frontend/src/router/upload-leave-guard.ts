import { confirmLeaveIfUploading } from '@/composables/use-confirm-leave';
import type { RouteLocationNormalized } from 'vue-router';

export async function uploadLeaveGuard(
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
): Promise<boolean | undefined> {
  if (to.path === from.path) {
    return undefined;
  }

  return (await confirmLeaveIfUploading()) ? undefined : false;
}
