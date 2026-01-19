import type { VueQueryPluginOptions } from '@tanstack/vue-query';

export const vueQueryPluginOptions: VueQueryPluginOptions = {
  queryClientConfig: {
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
        // Right now we don't have requests that need to be retried
        // That is because when a request fails, there is no reason that the next one would succeed
        // Tanstack will still refetch on widow focus or network reconnect
        retry: false,
      },
    },
  },
};

export enum QUERY_KEYS {
  MEETINGS = 'meetings',
  USERS = 'users',
  MEMBERS = 'members',
}
