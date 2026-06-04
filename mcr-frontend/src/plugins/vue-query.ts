import {
  MutationCache,
  QueryCache,
  QueryClient,
  type VueQueryPluginOptions,
} from '@tanstack/vue-query';
import { isUnexpectedHttpError, isRetryableError } from '@/services/http/http.utils';
import { reportError } from '@/services/observability/sentry';
import type { AppErrorMeta } from '@/services/observability/error-meta';

// Total wait time of ~30s (arbitrary)
const MAX_RETRIES = 5;

function shouldRetryGuard(failureCount: number, error: Error) {
  if (!isRetryableError(error)) return false;
  return failureCount < MAX_RETRIES;
}

export function handleMutationError(error: unknown, meta: AppErrorMeta | undefined): void {
  if (meta?.skipReport || !isUnexpectedHttpError(error)) return;
  reportError(error, { feature: meta?.feature ?? 'mutation' });
}

export function handleQueryError(error: unknown, meta: AppErrorMeta | undefined): void {
  if (meta?.skipReport || !isUnexpectedHttpError(error)) return;
  reportError(error, { feature: meta?.feature ?? 'query', level: 'warning' });
}

const queryClient = new QueryClient({
  mutationCache: new MutationCache({
    onError: (error, _variables, _context, mutation) => handleMutationError(error, mutation.meta),
  }),
  queryCache: new QueryCache({
    onError: (error, query) => handleQueryError(error, query.meta),
  }),
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: false,
    },
    mutations: {
      retry: shouldRetryGuard,
    },
  },
});

export const vueQueryPluginOptions: VueQueryPluginOptions = { queryClient };

export enum QUERY_KEYS {
  MEETINGS = 'meetings',
  USERS = 'users',
  MEMBERS = 'members',
  DELIVERABLES = 'deliverables',
}
