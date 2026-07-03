import { describe, it, expect, beforeEach, vi } from 'vitest';

async function freshComposable() {
  const { useUploadStatus } = await import('./use-upload-status');
  return useUploadStatus();
}

describe('useUploadStatus', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it('toggles hasActiveUploads on register/unregister', async () => {
    const { hasActiveUploads, registerUpload, unregisterUpload } = await freshComposable();
    expect(hasActiveUploads.value).toBe(false);

    const id = registerUpload({ abort: vi.fn() });
    expect(hasActiveUploads.value).toBe(true);

    unregisterUpload(id);
    expect(hasActiveUploads.value).toBe(false);
  });

  it('stays active while at least one upload remains', async () => {
    const { hasActiveUploads, registerUpload, unregisterUpload } = await freshComposable();

    const first = registerUpload({ abort: vi.fn() });
    const second = registerUpload({ abort: vi.fn() });

    unregisterUpload(first);
    expect(hasActiveUploads.value).toBe(true);

    unregisterUpload(second);
    expect(hasActiveUploads.value).toBe(false);
  });

  it('aborts every active upload', async () => {
    const { registerUpload, abortActiveUploads } = await freshComposable();
    const firstAbort = vi.fn();
    const secondAbort = vi.fn();
    registerUpload({ abort: firstAbort });
    registerUpload({ abort: secondAbort });

    abortActiveUploads();

    expect(firstAbort).toHaveBeenCalledTimes(1);
    expect(secondAbort).toHaveBeenCalledTimes(1);
  });

  it('unregisters immediately on abort so the guard cannot re-prompt for a dead import', async () => {
    const { hasActiveUploads, registerUpload, abortActiveUploads } = await freshComposable();
    registerUpload({ abort: vi.fn() });

    abortActiveUploads();

    expect(hasActiveUploads.value).toBe(false);
  });

  it('shares state across composable instances', async () => {
    const first = await freshComposable();
    const { useUploadStatus } = await import('./use-upload-status');
    const second = useUploadStatus();

    first.registerUpload({ abort: vi.fn() });
    expect(second.hasActiveUploads.value).toBe(true);
  });
});
