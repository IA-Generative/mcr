import { describe, it, expect, vi, beforeEach } from 'vitest';

const { reportError } = vi.hoisted(() => ({ reportError: vi.fn() }));
const {
  initMultipartUploadService,
  signMultipartPartService,
  completeMultipartUploadService,
  abortMultipartUploadService,
} = vi.hoisted(() => ({
  initMultipartUploadService: vi.fn(),
  signMultipartPartService: vi.fn(),
  completeMultipartUploadService: vi.fn(),
  abortMultipartUploadService: vi.fn(),
}));
const { put } = vi.hoisted(() => ({ put: vi.fn() }));

vi.mock('@/services/observability/sentry', () => ({ reportError }));
vi.mock('@/services/http/http.service', () => ({ default: { put } }));
vi.mock('@/services/meetings/meetings.service', () => ({
  initMultipartUploadService,
  signMultipartPartService,
  completeMultipartUploadService,
  abortMultipartUploadService,
  setFileHeaders: (_blob: Blob, headers: Record<string, unknown>) => headers,
}));
// run the mutationFn directly so we exercise the real orchestration
vi.mock('@tanstack/vue-query', () => ({
  useMutation: (config: { mutationFn: (vars: unknown) => unknown }) => ({
    mutateAsync: (vars: unknown) => Promise.resolve().then(() => config.mutationFn(vars)),
  }),
}));

import { useMultipart } from './use-multipart';

function makeFile() {
  return new File([new Uint8Array(10)], 'rec.m4a', { type: 'audio/m4a' });
}

function networkError() {
  return Object.assign(new Error('Network Error'), { code: 'ERR_NETWORK' });
}

describe('useMultipart.uploadFile', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    initMultipartUploadService.mockResolvedValue({ upload_id: 'u1', object_key: 'audio/1/x.m4a' });
    signMultipartPartService.mockResolvedValue('https://s3/put-url');
    completeMultipartUploadService.mockResolvedValue(undefined);
    abortMultipartUploadService.mockResolvedValue(undefined);
    put.mockResolvedValue({ headers: { etag: '"abc"' } });
  });

  it('completes a successful upload without reporting', async () => {
    const { uploadFile } = useMultipart();
    await uploadFile({ meetingId: 1, file: makeFile() });
    expect(completeMultipartUploadService).toHaveBeenCalledTimes(1);
    expect(reportError).not.toHaveBeenCalled();
  });

  it('reports once with rich context and re-throws the ORIGINAL error on a part failure', async () => {
    const err = networkError();
    put.mockRejectedValue(err);

    const { uploadFile } = useMultipart();
    await expect(uploadFile({ meetingId: 42, file: makeFile() })).rejects.toBe(err);

    expect(reportError).toHaveBeenCalledTimes(1);
    const [reported, opts] = reportError.mock.calls[0];
    expect(reported).toBe(err); // original cause, not a synthetic "Failed to upload file"
    expect(opts.feature).toBe('meeting.upload');
    expect(opts.contexts.upload).toMatchObject({
      phase: 'put', // the S3 PUT (crosses the user's network/proxy), not the presign
      partNumber: 1,
      axiosCode: 'ERR_NETWORK',
      online: expect.any(Boolean),
    });
    expect(abortMultipartUploadService).toHaveBeenCalledTimes(1); // best-effort cleanup
  });

  it('tags the phase as "sign" when the presign call fails (not the S3 PUT)', async () => {
    const err = networkError();
    signMultipartPartService.mockRejectedValue(err);

    const { uploadFile } = useMultipart();
    await expect(uploadFile({ meetingId: 7, file: makeFile() })).rejects.toBe(err);

    expect(put).not.toHaveBeenCalled(); // never reached the S3 PUT
    const [, opts] = reportError.mock.calls[0];
    expect(opts.contexts.upload).toMatchObject({ phase: 'sign', partNumber: 1 });
  });

  it('reports exactly once even when the abort also fails (silent abort)', async () => {
    put.mockRejectedValue(networkError());
    abortMultipartUploadService.mockRejectedValue(new Error('abort 500'));

    const { uploadFile } = useMultipart();
    await expect(uploadFile({ meetingId: 1, file: makeFile() })).rejects.toThrow('Network Error');
    expect(reportError).toHaveBeenCalledTimes(1);
  });

  it('does not produce an unhandled promise rejection on failure (regression: issue 2028)', async () => {
    put.mockRejectedValue(networkError());
    const onUnhandled = vi.fn();
    process.on('unhandledRejection', onUnhandled);

    const { uploadFile } = useMultipart();
    await uploadFile({ meetingId: 1, file: makeFile() }).catch(() => {});
    await new Promise((resolve) => setTimeout(resolve, 0));

    process.off('unhandledRejection', onUnhandled);
    expect(onUnhandled).not.toHaveBeenCalled();
  });
});
