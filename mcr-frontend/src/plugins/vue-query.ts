import { isRetryableError } from '@/services/http/http.utils';
import type { VueQueryPluginOptions } from '@tanstack/vue-query';

// Total wait time of ~30s (arbitrary)
const MAX_RETRIES = 5;

export const vueQueryPluginOptions: VueQueryPluginOptions = {
  queryClientConfig: {
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
        retry: false,
      },
      mutations: {
        retry: shouldRetryGuard,
      },
    },
  },
};

function shouldRetryGuard(failureCount: number, error: Error) {
  console.log(error);
  if (!isRetryableError(error)) return false;
  return failureCount < MAX_RETRIES;
}

export enum QUERY_KEYS {
  MEETINGS = 'meetings',
  USERS = 'users',
  MEMBERS = 'members',
  TRANSCRIPTION_WAIT_TIME = 'transcription-wait-time',
}
