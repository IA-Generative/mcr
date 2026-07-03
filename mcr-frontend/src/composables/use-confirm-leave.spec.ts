import { describe, it, expect, vi, beforeEach } from 'vitest';

type ModalAttrs = { onSuccess: () => void; onClosed: () => void };

const { useModal, open, destroy } = vi.hoisted(() => {
  const open = vi.fn();
  const destroy = vi.fn();
  const useModal = vi.fn(() => ({ open, destroy }));
  return { useModal, open, destroy };
});
const { uploadState, abortActiveUploads } = vi.hoisted(() => ({
  uploadState: { active: false },
  abortActiveUploads: vi.fn(),
}));

vi.mock('vue-final-modal', () => ({ useModal }));
vi.mock('@/plugins/i18n', () => ({ t: (key: string) => key }));
vi.mock('@/components/core/BaseModal.vue', () => ({ default: {} }));
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

import { confirmLeave, confirmLeaveIfUploading } from './use-confirm-leave';

function getModalAttrs(call = 0): ModalAttrs {
  return (useModal.mock.calls[call] as [{ attrs: ModalAttrs }])[0].attrs;
}

describe('confirmLeave', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('resolves true when the user confirms', async () => {
    const result = confirmLeave();
    const attrs = getModalAttrs();

    attrs.onSuccess();
    attrs.onClosed();

    await expect(result).resolves.toBe(true);
  });

  it('resolves false on any close without confirmation (ESC, outside click, cancel)', async () => {
    const result = confirmLeave();

    getModalAttrs().onClosed();

    await expect(result).resolves.toBe(false);
  });

  it('opens the modal and destroys it once settled', async () => {
    const result = confirmLeave();
    expect(open).toHaveBeenCalledTimes(1);

    getModalAttrs().onClosed();
    await result;

    expect(destroy).toHaveBeenCalledTimes(1);
  });
});

describe('confirmLeaveIfUploading', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    uploadState.active = false;
  });

  it('lets the caller proceed without prompting when nothing is uploading', async () => {
    await expect(confirmLeaveIfUploading()).resolves.toBe(true);
    expect(useModal).not.toHaveBeenCalled();
    expect(abortActiveUploads).not.toHaveBeenCalled();
  });

  it('denies the leave without aborting when the user refuses', async () => {
    uploadState.active = true;

    const result = confirmLeaveIfUploading();
    getModalAttrs().onClosed();

    await expect(result).resolves.toBe(false);
    expect(abortActiveUploads).not.toHaveBeenCalled();
  });

  it('aborts the uploads and lets the caller proceed when the user confirms', async () => {
    uploadState.active = true;

    const result = confirmLeaveIfUploading();
    const attrs = getModalAttrs();
    attrs.onSuccess();
    attrs.onClosed();

    await expect(result).resolves.toBe(true);
    expect(abortActiveUploads).toHaveBeenCalledTimes(1);
  });

  it('denies a concurrent caller while a confirmation is pending (single modal)', async () => {
    uploadState.active = true;

    const first = confirmLeaveIfUploading();
    await expect(confirmLeaveIfUploading()).resolves.toBe(false);
    expect(useModal).toHaveBeenCalledTimes(1);

    const attrs = getModalAttrs();
    attrs.onSuccess();
    attrs.onClosed();
    await expect(first).resolves.toBe(true);
  });

  it('prompts again once the previous confirmation settled', async () => {
    uploadState.active = true;

    const first = confirmLeaveIfUploading();
    getModalAttrs().onClosed();
    await first;

    const second = confirmLeaveIfUploading();
    expect(useModal).toHaveBeenCalledTimes(2);
    getModalAttrs(1).onClosed();
    await expect(second).resolves.toBe(false);
  });
});
