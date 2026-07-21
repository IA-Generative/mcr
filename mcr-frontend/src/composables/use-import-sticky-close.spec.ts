import { beforeEach, describe, expect, it, vi } from 'vitest';

const { confirmLeave, clearAll, abortActiveUploads, work } = vi.hoisted(() => ({
  confirmLeave: vi.fn(),
  clearAll: vi.fn(),
  abortActiveUploads: vi.fn(),
  work: { active: false },
}));

vi.mock('@/plugins/i18n', () => ({ t: (key: string) => key }));
vi.mock('@/composables/use-confirm-leave', () => ({ confirmLeave }));
vi.mock('@/composables/use-upload-batch', () => ({
  useUploadBatch: () => ({
    hasActiveWork: {
      get value() {
        return work.active;
      },
    },
  }),
  useUploadBatchWriter: () => ({ clearAll }),
}));
vi.mock('@/composables/use-upload-status', () => ({
  useUploadStatus: () => ({ abortActiveUploads }),
}));

import { useImportStickyClose } from './use-import-sticky-close';

describe('useImportStickyClose', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    work.active = false;
    confirmLeave.mockResolvedValue(false);
  });

  it('closes directly, without confirmation, when no work is active', async () => {
    const { close } = useImportStickyClose();

    await close();

    expect(confirmLeave).not.toHaveBeenCalled();
    expect(abortActiveUploads).not.toHaveBeenCalled();
    expect(clearAll).toHaveBeenCalledTimes(1);
  });

  it('aborts every upload and empties the store when the user confirms', async () => {
    work.active = true;
    confirmLeave.mockResolvedValue(true);
    const { close } = useImportStickyClose();

    await close();

    expect(confirmLeave).toHaveBeenCalledTimes(1);
    expect(abortActiveUploads).toHaveBeenCalledTimes(1);
    expect(clearAll).toHaveBeenCalledTimes(1);
  });

  it('leaves the uploads running when the user cancels', async () => {
    work.active = true;
    confirmLeave.mockResolvedValue(false);
    const { close } = useImportStickyClose();

    await close();

    expect(confirmLeave).toHaveBeenCalledTimes(1);
    expect(abortActiveUploads).not.toHaveBeenCalled();
    expect(clearAll).not.toHaveBeenCalled();
  });

  it('opens a single confirmation while one is already pending', async () => {
    work.active = true;
    let resolveConfirm!: (value: boolean) => void;
    confirmLeave.mockReturnValue(new Promise<boolean>((resolve) => (resolveConfirm = resolve)));
    const { close } = useImportStickyClose();

    const first = close();
    await close();
    expect(confirmLeave).toHaveBeenCalledTimes(1);

    resolveConfirm(true);
    await first;
    expect(abortActiveUploads).toHaveBeenCalledTimes(1);
  });
});
