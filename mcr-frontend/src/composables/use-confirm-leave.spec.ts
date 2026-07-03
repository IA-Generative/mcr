import { describe, it, expect, vi, beforeEach } from 'vitest';

type ModalAttrs = { onSuccess: () => void; onClosed: () => void };

const { useModal, open, destroy } = vi.hoisted(() => {
  const open = vi.fn();
  const destroy = vi.fn();
  const useModal = vi.fn(() => ({ open, destroy }));
  return { useModal, open, destroy };
});

vi.mock('vue-final-modal', () => ({ useModal }));
vi.mock('@/plugins/i18n', () => ({ t: (key: string) => key }));
vi.mock('@/components/core/BaseModal.vue', () => ({ default: {} }));

import { confirmLeave } from './use-confirm-leave';

function getModalAttrs(): ModalAttrs {
  return useModal.mock.calls[0][0].attrs as ModalAttrs;
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
