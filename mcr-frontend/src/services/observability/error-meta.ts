import type { Feature } from '@/services/observability/sentry';

/**
 * Per-query/per-mutation telemetry policy, read by the vue-query cache `onError`
 * handlers (the "floor"). Typed onto TanStack's `Register` so `meta` is checked
 * at every `useMutation`/`useQuery` call site and in the cache handlers.
 */
export interface AppErrorMeta {
  /**
   * Feature tag the floor uses when it captures this error. `meeting.upload`
   * is excluded on purpose: uploads self-report at their boundary with rich
   * context, so the floor must never emit a context-less upload event.
   */
  feature?: Exclude<Feature, 'meeting.upload'>;
  /** Opt OUT of the floor — this flow self-reports at a domain boundary. */
  skipReport?: boolean;
}

declare module '@tanstack/vue-query' {
  interface Register {
    mutationMeta: AppErrorMeta & Record<string, unknown>;
    queryMeta: AppErrorMeta & Record<string, unknown>;
  }
}
