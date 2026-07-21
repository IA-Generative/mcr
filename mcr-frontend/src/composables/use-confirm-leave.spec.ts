import { describe, it, expect, vi, beforeEach } from 'vitest';

type ModalAttrs = { onSuccess: () => void; onClosed: () => void };

const { useModal, open, destroy } = vi.hoisted(() => {
  const open = vi.fn();
  const destroy = vi.fn();
  const useModal = vi.fn((_options: { attrs: ModalAttrs }) => ({ open, destroy }));
  return { useModal, open, destroy };
});
const { work, abortActiveUploads, clearAll } = vi.hoisted(() => ({
  work: { active: false },
  abortActiveUploads: vi.fn(),
  clearAll: vi.fn(),
}));

vi.mock('vue-final-modal', () => ({ useModal }));
vi.mock('@/plugins/i18n', () => ({ t: (key: string) => key }));
vi.mock('@/components/core/BaseModal.vue', () => ({ default: {} }));
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

import {
  confirmAbortActiveUploads,
  confirmLeave,
  confirmLeaveIfUploading,
  dialogFor,
} from './use-confirm-leave';

const dialog = { title: 'title', text: 'text', ctaLabel: 'cta' };

function getModalAttrs(call = 0): ModalAttrs {
  return useModal.mock.calls[call][0].attrs;
}

describe('dialogFor', () => {
  it('maps an i18n namespace to the modal title, text and cta', () => {
    expect(dialogFor('meeting.import.confirm-close')).toEqual({
      title: 'meeting.import.confirm-close.title',
      text: 'meeting.import.confirm-close.description',
      ctaLabel: 'meeting.import.confirm-close.button',
    });
  });
});

describe('confirmLeave', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('resolves true when the user confirms', async () => {
    const result = confirmLeave(dialog);
    const attrs = getModalAttrs();

    attrs.onSuccess();
    attrs.onClosed();

    await expect(result).resolves.toBe(true);
  });

  it('resolves false on any close without confirmation (ESC, outside click, cancel)', async () => {
    const result = confirmLeave(dialog);

    getModalAttrs().onClosed();

    await expect(result).resolves.toBe(false);
  });

  it('opens the modal and destroys it once settled', async () => {
    const result = confirmLeave(dialog);
    expect(open).toHaveBeenCalledTimes(1);

    getModalAttrs().onClosed();
    await result;

    expect(destroy).toHaveBeenCalledTimes(1);
  });
});

describe('confirmAbortActiveUploads', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    work.active = false;
  });

  it('lets the caller proceed without prompting or touching anything when nothing is running', async () => {
    await expect(confirmAbortActiveUploads(dialog)).resolves.toBe(true);
    expect(useModal).not.toHaveBeenCalled();
    expect(abortActiveUploads).not.toHaveBeenCalled();
    expect(clearAll).not.toHaveBeenCalled();
  });

  it('aborts every upload and empties the store when the user confirms', async () => {
    work.active = true;

    const result = confirmAbortActiveUploads(dialog);
    const attrs = getModalAttrs();
    attrs.onSuccess();
    attrs.onClosed();

    await expect(result).resolves.toBe(true);
    expect(abortActiveUploads).toHaveBeenCalledTimes(1);
    expect(clearAll).toHaveBeenCalledTimes(1);
  });

  it('changes nothing when the user refuses', async () => {
    work.active = true;

    const result = confirmAbortActiveUploads(dialog);
    getModalAttrs().onClosed();

    await expect(result).resolves.toBe(false);
    expect(abortActiveUploads).not.toHaveBeenCalled();
    expect(clearAll).not.toHaveBeenCalled();
  });

  it('denies a concurrent caller while a confirmation is pending (single modal)', async () => {
    work.active = true;

    const first = confirmAbortActiveUploads(dialog);
    await expect(confirmAbortActiveUploads(dialog)).resolves.toBe(false);
    expect(useModal).toHaveBeenCalledTimes(1);

    const attrs = getModalAttrs();
    attrs.onSuccess();
    attrs.onClosed();
    await expect(first).resolves.toBe(true);
  });

  it('prompts again once the previous confirmation settled', async () => {
    work.active = true;

    const first = confirmAbortActiveUploads(dialog);
    getModalAttrs().onClosed();
    await first;

    const second = confirmAbortActiveUploads(dialog);
    expect(useModal).toHaveBeenCalledTimes(2);
    getModalAttrs(1).onClosed();
    await expect(second).resolves.toBe(false);
  });
});

describe('confirmLeaveIfUploading', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    work.active = false;
  });

  it('aborts and empties the store when the user confirms leaving', async () => {
    work.active = true;

    const result = confirmLeaveIfUploading();
    const attrs = getModalAttrs();
    attrs.onSuccess();
    attrs.onClosed();

    await expect(result).resolves.toBe(true);
    expect(abortActiveUploads).toHaveBeenCalledTimes(1);
    expect(clearAll).toHaveBeenCalledTimes(1);
  });
});
