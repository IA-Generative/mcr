import { describe, it, expect } from 'vitest';
import { classifyUploadFailure } from './http.utils';

function axiosError(opts: { status?: number; code?: string }) {
  const error: Record<string, unknown> = { code: opts.code };
  if (opts.status !== undefined) error.response = { status: opts.status };
  return Object.assign(new Error('upload failed'), error);
}

describe('classifyUploadFailure', () => {
  it('classifies a no-response ERR_NETWORK while online as "blocked"', () => {
    expect(classifyUploadFailure(axiosError({ code: 'ERR_NETWORK' }), true)).toBe('blocked');
  });

  it('classifies any no-response failure while offline as "offline"', () => {
    expect(classifyUploadFailure(axiosError({ code: 'ERR_NETWORK' }), false)).toBe('offline');
  });

  it('classifies a timeout as "timeout"', () => {
    expect(classifyUploadFailure(axiosError({ code: 'ECONNABORTED' }), true)).toBe('timeout');
    expect(classifyUploadFailure(axiosError({ code: 'ETIMEDOUT' }), true)).toBe('timeout');
  });

  it('classifies a readable 4xx as "http-client" (a response did arrive)', () => {
    expect(classifyUploadFailure(axiosError({ status: 403 }), true)).toBe('http-client');
  });

  it('classifies a readable 5xx as "http-server"', () => {
    expect(classifyUploadFailure(axiosError({ status: 503 }), true)).toBe('http-server');
  });

  it('falls back to "unknown" for an unrecognised no-response error', () => {
    expect(classifyUploadFailure(axiosError({ code: 'ERR_FOO' }), true)).toBe('unknown');
  });
});
