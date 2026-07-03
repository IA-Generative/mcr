import { describe, it, expect, vi, beforeEach } from 'vitest';

const { confirmLeave } = vi.hoisted(() => ({ confirmLeave: vi.fn() }));
const { uploadState, abortActiveUploads } = vi.hoisted(() => ({
  uploadState: { active: false },
  abortActiveUploads: vi.fn(),
}));

vi.mock('@/composables/use-confirm-leave', () => ({ confirmLeave }));
vi.mock('@/composables/use-upload-status', () => ({
  useUploadStatus: () => ({
    hasActiveUploads: {
      get value() {
        return uploadState.active;
      },
    },
    abortActiveUploads,
  }),
}));

import { createUploadLeaveGuard } from './upload-leave-guard';

describe('createUploadLeaveGuard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    uploadState.active = false;
  });

  it('lets navigation through when no upload is active, without prompting', async () => {
    const guard = createUploadLeaveGuard();
    await expect(guard()).resolves.toBeUndefined();
    expect(confirmLeave).not.toHaveBeenCalled();
  });

  it('blocks navigation when the user refuses to leave', async () => {
    uploadState.active = true;
    confirmLeave.mockResolvedValue(false);

    const guard = createUploadLeaveGuard();
    await expect(guard()).resolves.toBe(false);
    expect(abortActiveUploads).not.toHaveBeenCalled();
  });

  it('aborts active uploads and lets navigation through when the user confirms', async () => {
    uploadState.active = true;
    confirmLeave.mockResolvedValue(true);

    const guard = createUploadLeaveGuard();
    await expect(guard()).resolves.toBeUndefined();
    expect(abortActiveUploads).toHaveBeenCalledTimes(1);
  });

  it('blocks a second navigation while a confirmation is already pending (no stacked modals)', async () => {
    uploadState.active = true;
    let resolveConfirm!: (leave: boolean) => void;
    confirmLeave.mockImplementation(
      () =>
        new Promise<boolean>((resolve) => {
          resolveConfirm = resolve;
        }),
    );

    const guard = createUploadLeaveGuard();
    const first = guard();
    await expect(guard()).resolves.toBe(false);
    expect(confirmLeave).toHaveBeenCalledTimes(1);

    resolveConfirm(true);
    await expect(first).resolves.toBeUndefined();
  });

  it('prompts again on a later navigation once the previous confirmation settled', async () => {
    uploadState.active = true;
    confirmLeave.mockResolvedValue(false);

    const guard = createUploadLeaveGuard();
    await guard();
    await guard();
    expect(confirmLeave).toHaveBeenCalledTimes(2);
  });
});
