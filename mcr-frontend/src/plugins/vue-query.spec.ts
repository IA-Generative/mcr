import { describe, it, expect, vi, beforeEach } from 'vitest';

const { reportError } = vi.hoisted(() => ({ reportError: vi.fn() }));
vi.mock('@/services/observability/sentry', () => ({ reportError }));

import { handleMutationError, handleQueryError } from './vue-query';
import { SessionExpiredError } from '@/services/auth/token-provider';

describe('vue-query error floor', () => {
  beforeEach(() => vi.clearAllMocks());

  it('reports a mutation error with the default feature', () => {
    handleMutationError(new Error('e'), undefined);
    expect(reportError).toHaveBeenCalledWith(expect.any(Error), { feature: 'mutation' });
  });

  it('uses meta.feature when provided', () => {
    handleMutationError(new Error('e'), { feature: 'meeting.create' });
    expect(reportError).toHaveBeenCalledWith(expect.any(Error), { feature: 'meeting.create' });
  });

  it('skips reporting when meta.skipReport is set (boundary owns it)', () => {
    handleMutationError(new Error('e'), { skipReport: true });
    expect(reportError).not.toHaveBeenCalled();
  });

  it('reports query errors at warning level', () => {
    handleQueryError(new Error('e'), undefined);
    expect(reportError).toHaveBeenCalledWith(expect.any(Error), {
      feature: 'query',
      level: 'warning',
    });
  });

  it('does not report expected client errors (4xx)', () => {
    handleMutationError({ response: { status: 404 } }, undefined);
    handleQueryError({ response: { status: 403 } }, undefined);
    expect(reportError).not.toHaveBeenCalled();
  });

  it('does not report an expired session (expected auth-lifecycle event)', () => {
    handleMutationError(new SessionExpiredError(), undefined);
    handleQueryError(new SessionExpiredError(), undefined);
    expect(reportError).not.toHaveBeenCalled();
  });

  it('reports server errors (5xx)', () => {
    handleMutationError({ response: { status: 500 } }, undefined);
    expect(reportError).toHaveBeenCalledWith(
      { response: { status: 500 } },
      { feature: 'mutation' },
    );
  });
});
