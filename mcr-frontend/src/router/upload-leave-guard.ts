import { confirmLeaveIfUploading } from '@/composables/use-confirm-leave';
import type { RouteLocationNormalized } from 'vue-router';

export async function uploadLeaveGuard(
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
): Promise<boolean | undefined> {
  // a query/hash-only change does not unload the page, so it cannot lose the upload
  if (to.path === from.path) return undefined;
  return (await confirmLeaveIfUploading()) ? undefined : false;
}
