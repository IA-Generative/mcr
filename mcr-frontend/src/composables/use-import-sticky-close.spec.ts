import { beforeEach, describe, expect, it, vi } from 'vitest';

const { confirmAbortActiveUploads, clearAll, work } = vi.hoisted(() => ({
  confirmAbortActiveUploads: vi.fn(),
  clearAll: vi.fn(),
  work: { active: false },
}));

vi.mock('@/composables/use-confirm-leave', () => ({
  confirmAbortActiveUploads,
  dialogFor: (namespace: string) => ({
    title: `${namespace}.title`,
    text: `${namespace}.description`,
    ctaLabel: `${namespace}.button`,
  }),
}));
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

import { useImportStickyClose } from './use-import-sticky-close';

describe('useImportStickyClose', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    work.active = false;
    confirmAbortActiveUploads.mockResolvedValue(true);
  });

  it('closes directly, without confirmation, when no work is active', async () => {
    const { close } = useImportStickyClose();

    await close();

    expect(confirmAbortActiveUploads).not.toHaveBeenCalled();
    expect(clearAll).toHaveBeenCalledTimes(1);
  });

  it('delegates to the shared confirm-and-abort guard while work is active, without clearing again', async () => {
    work.active = true;
    const { close } = useImportStickyClose();

    await close();

    expect(clearAll).not.toHaveBeenCalled();
    expect(confirmAbortActiveUploads).toHaveBeenCalledWith({
      title: 'meeting.import.confirm-close.title',
      text: 'meeting.import.confirm-close.description',
      ctaLabel: 'meeting.import.confirm-close.button',
    });
  });
});
