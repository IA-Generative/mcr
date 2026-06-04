import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { App } from 'vue';

const { init, consoleLoggingIntegration, captureException } = vi.hoisted(() => ({
  init: vi.fn(),
  consoleLoggingIntegration: vi.fn(() => ({ name: 'console' })),
  captureException: vi.fn(),
}));
vi.mock('@sentry/vue', () => ({ init, consoleLoggingIntegration, captureException }));

import { initSentry, reportError } from './sentry';

const PRESIGNED_URL =
  'https://s3.fr-par.scw.cloud/bucket/audio/1/x.m4a?uploadId=ABC&X-Amz-Signature=secret';

function initAndGetOptions() {
  vi.stubGlobal('window', { ENV_MODE: 'PROD', VITE_SENTRY_FRONTEND_DSN: 'https://dsn' });
  initSentry({} as App);
  return init.mock.calls[0][0];
}

function fakeScope() {
  return { setTag: vi.fn(), setLevel: vi.fn(), setContext: vi.fn() };
}

type ScopeCallback = (scope: ReturnType<typeof fakeScope>) => void;

describe('initSentry', () => {
  beforeEach(() => vi.clearAllMocks());

  it('does not initialize when the environment is not set', () => {
    vi.stubGlobal('window', {});
    initSentry({} as App);
    expect(init).not.toHaveBeenCalled();
  });

  it('redacts the query string of http breadcrumb urls', () => {
    const options = initAndGetOptions();
    const result = options.beforeBreadcrumb({ category: 'xhr', data: { url: PRESIGNED_URL } });
    expect(result.data.url).toBe('https://s3.fr-par.scw.cloud/bucket/audio/1/x.m4a?[redacted]');
  });

  it('leaves non-http breadcrumbs untouched', () => {
    const options = initAndGetOptions();
    const crumb = { category: 'ui.click', message: 'button' };
    expect(options.beforeBreadcrumb(crumb)).toEqual(crumb);
  });

  it('redacts request url query and strips auth headers from the event', () => {
    const options = initAndGetOptions();
    const event = options.beforeSend({
      request: {
        url: PRESIGNED_URL,
        headers: { Authorization: 'Bearer t', 'X-User-Access-Token': 'tok', 'X-Keep': 'ok' },
      },
    });
    expect(event.request.url).toBe('https://s3.fr-par.scw.cloud/bucket/audio/1/x.m4a?[redacted]');
    expect(event.request.headers).toEqual({ 'X-Keep': 'ok' });
  });
});

describe('reportError', () => {
  beforeEach(() => vi.clearAllMocks());

  it('captures the error once and sets the feature tag', () => {
    reportError(new Error('boom'), { feature: 'mutation' });

    expect(captureException).toHaveBeenCalledTimes(1);
    const [err, cb] = captureException.mock.calls[0] as [unknown, ScopeCallback];
    expect(err).toBeInstanceOf(Error);

    const scope = fakeScope();
    cb(scope);
    expect(scope.setTag).toHaveBeenCalledWith('feature', 'mutation');
  });

  it('forwards level, custom tags and contexts to the scope', () => {
    reportError(new Error('x'), {
      feature: 'meeting.upload',
      level: 'warning',
      tags: { 'meeting.id': 7, 'upload.phase': 'put' },
      contexts: {
        upload: {
          phase: 'put',
          totalParts: 2,
          fileSize: 10,
          bytesSent: 0,
          durationMs: 5,
          online: true,
        },
      },
    });

    const cb = captureException.mock.calls[0][1] as ScopeCallback;
    const scope = fakeScope();
    cb(scope);

    expect(scope.setLevel).toHaveBeenCalledWith('warning');
    expect(scope.setTag).toHaveBeenCalledWith('feature', 'meeting.upload');
    expect(scope.setTag).toHaveBeenCalledWith('meeting.id', 7);
    expect(scope.setTag).toHaveBeenCalledWith('upload.phase', 'put');
    expect(scope.setContext).toHaveBeenCalledWith(
      'upload',
      expect.objectContaining({ phase: 'put' }),
    );
  });
});
