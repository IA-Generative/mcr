import { describe, it, expect } from 'vitest';
import { defineComponent, h } from 'vue';
import { waitFor } from '@testing-library/vue';
import { createPinia, setActivePinia } from 'pinia';
import { renderWithPlugins } from '@/vitest.setup';
import { useDeliverableFeedbackDraft } from '@/services/deliverable-feedback/use-deliverable-feedback-draft';
import { shouldPollDeliverables, useDeliverables } from './use-deliverables';
import type { DeliverableDto, DeliverableStatus } from './deliverables.types';

const { fetchDeliverables } = vi.hoisted(() => ({ fetchDeliverables: vi.fn() }));

vi.mock('./deliverables.service', () => ({
  getMeetingDeliverables: (...args: unknown[]) => fetchDeliverables(...args),
  createDeliverable: vi.fn(),
  downloadDeliverableFile: vi.fn(),
}));

function deliverable(
  status: DeliverableStatus,
  overrides: Partial<DeliverableDto> = {},
): DeliverableDto {
  return {
    id: 1,
    meeting_id: 1,
    type: 'TRANSCRIPTION',
    status,
    external_url: null,
    created_at: '2026-07-10T00:00:00Z',
    updated_at: '2026-07-10T00:00:00Z',
    feedback: null,
    ...overrides,
  };
}

describe('shouldPollDeliverables', () => {
  it.each(['REQUESTED', 'PENDING', 'IN_PROGRESS'] satisfies DeliverableStatus[])(
    'should_keep_polling_while_a_deliverable_is_%s',
    (status) => {
      expect(shouldPollDeliverables([deliverable('AVAILABLE'), deliverable(status)])).toBe(true);
    },
  );

  it.each(['AVAILABLE', 'FAILED'] satisfies DeliverableStatus[])(
    'should_stop_polling_when_all_deliverables_are_settled_like_%s',
    (status) => {
      expect(shouldPollDeliverables([deliverable(status)])).toBe(false);
    },
  );

  it('should_not_poll_before_the_list_is_loaded', () => {
    expect(shouldPollDeliverables(undefined)).toBe(false);
  });
});

describe('getDeliverablesQuery, seeding the feedback drafts', () => {
  function rated(
    feedback: DeliverableDto['feedback'],
    overrides: Partial<DeliverableDto> = {},
  ): DeliverableDto {
    return deliverable('AVAILABLE', { id: 42, feedback, ...overrides });
  }

  function renderHost() {
    let query: ReturnType<ReturnType<typeof useDeliverables>['getDeliverablesQuery']>;
    const Host = defineComponent({
      setup() {
        query = useDeliverables().getDeliverablesQuery(1);
        return () => h('div');
      },
    });
    renderWithPlugins(Host);
    return { refetch: () => query.refetch() };
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('makes the opinion held in base available for pre-filling once the deliverables have loaded', async () => {
    fetchDeliverables.mockResolvedValue({
      deliverables: [rated({ vote_type: 'POSITIVE', comment: 'bien', reasons: [] })],
    });
    const drafts = useDeliverableFeedbackDraft();

    renderHost();

    await waitFor(() => expect(drafts.draftFor(42, 'POSITIVE')?.comment).toBe('bien'));
  });

  it('does not let a refetch overwrite what the user typed without submitting', async () => {
    fetchDeliverables.mockResolvedValue({
      deliverables: [rated({ vote_type: 'POSITIVE', comment: 'bien', reasons: [] })],
    });
    const drafts = useDeliverableFeedbackDraft();
    const { refetch } = renderHost();
    await waitFor(() => expect(drafts.draftFor(42, 'POSITIVE')).toBeDefined());
    drafts.remember(42, { vote_type: 'POSITIVE', comment: 'bien, mais à nuancer', reasons: [] });

    // A payload identical to the previous one keeps its object reference through the query's
    // structural sharing, so nothing would be re-seeded and the test would prove nothing.
    fetchDeliverables.mockResolvedValue({
      deliverables: [
        rated(
          { vote_type: 'POSITIVE', comment: 'bien', reasons: [] },
          { updated_at: '2026-07-11T00:00:00Z' },
        ),
      ],
    });
    await refetch();

    expect(drafts.draftFor(42, 'POSITIVE')?.comment).toBe('bien, mais à nuancer');
  });

  it('keeps the memory across a refetch that no longer carries the feedback', async () => {
    fetchDeliverables.mockResolvedValue({
      deliverables: [rated({ vote_type: 'POSITIVE', comment: 'bien', reasons: [] })],
    });
    const drafts = useDeliverableFeedbackDraft();
    const { refetch } = renderHost();
    await waitFor(() => expect(drafts.draftFor(42, 'POSITIVE')).toBeDefined());

    fetchDeliverables.mockResolvedValue({ deliverables: [rated(null)] });
    await refetch();

    expect(drafts.draftFor(42, 'POSITIVE')?.comment).toBe('bien');
  });
});
