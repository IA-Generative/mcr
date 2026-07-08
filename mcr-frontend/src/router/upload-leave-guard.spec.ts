import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { RouteLocationNormalized } from 'vue-router';

const { confirmLeaveIfUploading } = vi.hoisted(() => ({ confirmLeaveIfUploading: vi.fn() }));

vi.mock('@/composables/use-confirm-leave', () => ({ confirmLeaveIfUploading }));

import { uploadLeaveGuard } from './upload-leave-guard';

function route(path: string) {
  return { path } as RouteLocationNormalized;
}

describe('uploadLeaveGuard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('ignores same-path navigations (query/hash changes cannot lose the upload)', async () => {
    await expect(uploadLeaveGuard(route('/meetings'), route('/meetings'))).resolves.toBeUndefined();
    expect(confirmLeaveIfUploading).not.toHaveBeenCalled();
  });

  it('lets the navigation through when leaving is allowed', async () => {
    confirmLeaveIfUploading.mockResolvedValue(true);

    await expect(uploadLeaveGuard(route('/meetings/7'), route('/'))).resolves.toBeUndefined();
  });

  it('blocks the navigation when leaving is denied', async () => {
    confirmLeaveIfUploading.mockResolvedValue(false);

    await expect(uploadLeaveGuard(route('/meetings/7'), route('/'))).resolves.toBe(false);
  });
});
