import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query';
import { flushPromises } from '@vue/test-utils';
import { defineComponent, h } from 'vue';
import { render } from '@testing-library/vue';
import { QUERY_KEYS } from '@/plugins/vue-query';
import type { DeliverableListResponse } from '@/services/deliverables/deliverables.types';

const { upsert, remove } = vi.hoisted(() => ({ upsert: vi.fn(), remove: vi.fn() }));

vi.mock('./deliverable-feedback.service', () => ({
  upsertDeliverableFeedback: (...args: unknown[]) => upsert(...args),
  deleteDeliverableFeedback: (...args: unknown[]) => remove(...args),
}));

import { useDeliverableFeedback } from './use-deliverable-feedback';

const MEETING_ID = 1;
const KEY = [QUERY_KEYS.DELIVERABLES, MEETING_ID];

function seededClient(feedback: DeliverableListResponse['deliverables'][0]['feedback']) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  queryClient.setQueryData<DeliverableListResponse>(KEY, {
    deliverables: [
      {
        id: 42,
        meeting_id: MEETING_ID,
        type: 'DECISION_RECORD',
        status: 'AVAILABLE',
        external_url: null,
        created_at: '2026-07-30T00:00:00Z',
        updated_at: '2026-07-30T00:00:00Z',
        feedback,
      },
    ],
  });
  return queryClient;
}

function mountComposable(queryClient: QueryClient) {
  let api!: ReturnType<typeof useDeliverableFeedback>;
  const Host = defineComponent({
    setup() {
      api = useDeliverableFeedback(MEETING_ID);
      return () => h('div');
    },
  });
  render(Host, { global: { plugins: [[VueQueryPlugin, { queryClient }]] } });
  return api;
}

function cachedFeedback(queryClient: QueryClient) {
  return queryClient.getQueryData<DeliverableListResponse>(KEY)!.deliverables[0].feedback;
}

describe('useDeliverableFeedback optimistic cache', () => {
  beforeEach(() => vi.clearAllMocks());

  it('shows the vote as cast before the server answers', async () => {
    let release: () => void = () => {};
    upsert.mockImplementation(() => new Promise<void>((resolve) => (release = resolve)));
    const queryClient = seededClient(null);
    const { upsertMutation } = mountComposable(queryClient);

    upsertMutation.mutate({
      deliverableId: 42,
      payload: { vote_type: 'POSITIVE', comment: 'clair' },
    });
    await flushPromises();

    expect(cachedFeedback(queryClient)).toEqual({
      vote_type: 'POSITIVE',
      comment: 'clair',
      reasons: [],
    });
    release();
  });

  it('empties the vote before the server answers a retraction', async () => {
    let release: () => void = () => {};
    remove.mockImplementation(() => new Promise<void>((resolve) => (release = resolve)));
    const queryClient = seededClient({ vote_type: 'POSITIVE', comment: 'bien', reasons: [] });
    const { removeMutation } = mountComposable(queryClient);

    removeMutation.mutate(42);
    await flushPromises();

    expect(cachedFeedback(queryClient)).toBeNull();
    release();
  });

  it('puts the previous vote back when the retraction fails', async () => {
    remove.mockRejectedValue(new Error('boom'));
    const queryClient = seededClient({ vote_type: 'POSITIVE', comment: 'bien', reasons: [] });
    const { removeMutation } = mountComposable(queryClient);

    removeMutation.mutate(42);
    await flushPromises();
    await flushPromises();

    expect(cachedFeedback(queryClient)).toEqual({
      vote_type: 'POSITIVE',
      comment: 'bien',
      reasons: [],
    });
  });

  it('puts the absence of a vote back when the submission fails', async () => {
    upsert.mockRejectedValue(new Error('boom'));
    const queryClient = seededClient(null);
    const { upsertMutation } = mountComposable(queryClient);

    upsertMutation.mutate({ deliverableId: 42, payload: { vote_type: 'POSITIVE' } });
    await flushPromises();
    await flushPromises();

    expect(cachedFeedback(queryClient)).toBeNull();
  });

  it('leaves other deliverables of the meeting untouched', async () => {
    upsert.mockResolvedValue({ vote_type: 'POSITIVE', comment: null });
    const queryClient = seededClient(null);
    const existing = queryClient.getQueryData<DeliverableListResponse>(KEY)!;
    queryClient.setQueryData<DeliverableListResponse>(KEY, {
      deliverables: [
        ...existing.deliverables,
        { ...existing.deliverables[0], id: 99, type: 'DETAILED_SYNTHESIS' },
      ],
    });
    const { upsertMutation } = mountComposable(queryClient);

    upsertMutation.mutate({ deliverableId: 42, payload: { vote_type: 'POSITIVE' } });
    await flushPromises();

    const rows = queryClient.getQueryData<DeliverableListResponse>(KEY)!.deliverables;
    expect(rows.find((d) => d.id === 99)!.feedback).toBeNull();
  });
});
