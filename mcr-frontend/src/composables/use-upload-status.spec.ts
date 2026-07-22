import { describe, it, expect, beforeEach, vi } from 'vitest';

async function freshComposable() {
  const { useUploadStatus } = await import('./use-upload-status');
  return useUploadStatus();
}

describe('useUploadStatus', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it('aborts every registered upload', async () => {
    const { registerUpload, abortActiveUploads } = await freshComposable();
    const firstAbort = vi.fn();
    const secondAbort = vi.fn();
    registerUpload({ abort: firstAbort });
    registerUpload({ abort: secondAbort });

    abortActiveUploads();

    expect(firstAbort).toHaveBeenCalledTimes(1);
    expect(secondAbort).toHaveBeenCalledTimes(1);
  });

  it('never aborts an upload that was unregistered beforehand', async () => {
    const { registerUpload, unregisterUpload, abortActiveUploads } = await freshComposable();
    const abort = vi.fn();
    const id = registerUpload({ abort });

    unregisterUpload(id);
    abortActiveUploads();

    expect(abort).not.toHaveBeenCalled();
  });

  it('drops each upload before aborting it so a second abort is a no-op', async () => {
    const { registerUpload, abortActiveUploads } = await freshComposable();
    const abort = vi.fn();
    registerUpload({ abort });

    abortActiveUploads();
    abortActiveUploads();

    expect(abort).toHaveBeenCalledTimes(1);
  });

  it('shares the registry across composable instances', async () => {
    const first = await freshComposable();
    const { useUploadStatus } = await import('./use-upload-status');
    const second = useUploadStatus();
    const abort = vi.fn();

    first.registerUpload({ abort });
    second.abortActiveUploads();

    expect(abort).toHaveBeenCalledTimes(1);
  });
});
