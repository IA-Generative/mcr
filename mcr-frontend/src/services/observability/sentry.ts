import * as Sentry from '@sentry/vue';
import type { Contexts, SeverityLevel } from '@sentry/vue';
import type { App } from 'vue';

type Primitive = string | number | boolean;

// Closed set of features — call sites cannot invent arbitrary feature tags.
export type Feature =
  | 'meeting.upload'
  | 'meeting.create'
  | 'recording'
  | 'transcription'
  | 'mutation'
  | 'query';

export interface UploadContext {
  phase: 'init' | 'sign' | 'put' | 'complete';
  partNumber?: number;
  totalParts: number;
  fileSize: number;
  bytesSent: number;
  durationMs: number;
  httpStatus?: number;
  axiosCode?: string;
  online: boolean;
  effectiveType?: string | null;
  // allow assignment to Sentry's `Context` (Record<string, unknown>)
  [key: string]: unknown;
}

interface BaseReport {
  tags?: Record<string, Primitive>;
  level?: SeverityLevel; // default 'error'
}

/**
 * Discriminated on `feature`: a `meeting.upload` report MUST carry a typed
 * `upload` context, so call sites can't forget or misname a field.
 */
export type ReportOptions =
  | (BaseReport & { feature: 'meeting.upload'; contexts: { upload: UploadContext } })
  | (BaseReport & { feature: Exclude<Feature, 'meeting.upload'>; contexts?: Contexts });

export function reportError(error: unknown, opts: ReportOptions): void {
  Sentry.captureException(error, (scope) => {
    scope.setTag('feature', opts.feature);
    if (opts.level) scope.setLevel(opts.level);
    if (opts.tags) {
      for (const [key, value] of Object.entries(opts.tags)) scope.setTag(key, value);
    }
    if (opts.contexts) {
      for (const [key, value] of Object.entries(opts.contexts))
        scope.setContext(key, value ?? null);
    }
    return scope;
  });
}

function redactQueryString(url?: string): string | undefined {
  if (!url) return url;
  const queryIndex = url.indexOf('?');
  return queryIndex === -1 ? url : `${url.slice(0, queryIndex)}?[redacted]`;
}

// Presigned upload URLs carry their signature in the query string.
function scrubBreadcrumb(breadcrumb: Sentry.Breadcrumb): Sentry.Breadcrumb {
  const isHttpBreadcrumb = breadcrumb.category === 'xhr' || breadcrumb.category === 'fetch';
  if (isHttpBreadcrumb && typeof breadcrumb.data?.url === 'string') {
    breadcrumb.data.url = redactQueryString(breadcrumb.data.url);
  }
  return breadcrumb;
}

function scrubRequest(event: Sentry.ErrorEvent): Sentry.ErrorEvent {
  if (event.request?.url) {
    event.request.url = redactQueryString(event.request.url);
  }
  if (event.request?.headers) {
    delete event.request.headers['Authorization'];
    delete event.request.headers['X-User-Access-Token'];
  }
  return event;
}

function resolveSentryConfig() {
  const environment = (window as any).ENV_MODE || import.meta.env.VITE_ENV_MODE;
  const dsn = (window as any).VITE_SENTRY_FRONTEND_DSN || import.meta.env.VITE_SENTRY_FRONTEND_DSN;
  return { environment, dsn };
}

export function initSentry(app: App): void {
  const { environment, dsn } = resolveSentryConfig();
  if (!environment) return;

  Sentry.init({
    app,
    dsn,
    environment,
    sendDefaultPii: true,
    enableLogs: true,
    integrations: [Sentry.consoleLoggingIntegration({ levels: ['info', 'warn', 'error'] })],
    tracesSampleRate: 1.0,
    beforeBreadcrumb: scrubBreadcrumb,
    beforeSend: scrubRequest,
  });
}
