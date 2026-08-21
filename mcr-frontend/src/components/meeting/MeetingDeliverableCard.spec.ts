import { describe, it, expect, vi } from 'vitest';
import { ref } from 'vue';
import { screen } from '@testing-library/vue';
import userEvent from '@testing-library/user-event';

const { createMutate } = vi.hoisted(() => ({ createMutate: vi.fn() }));

vi.mock('@/services/deliverables/use-deliverables', () => ({
  useDeliverables: () => ({
    getDeliverablesQuery: () => ({ data: ref([]) }),
    createDeliverableMutation: () => ({ mutate: createMutate }),
    downloadDeliverableMutation: () => ({ mutate: vi.fn() }),
  }),
}));

// DeliverableTypeCard (child) reads a feature flag; stub it so Unleash isn't hit in tests.
vi.mock('@/composables/use-feature-flag', () => ({ useFeatureFlag: () => ref(false) }));
vi.mock('@/composables/use-toaster', () => ({ default: () => ({ addErrorMessage: vi.fn() }) }));
vi.mock('vue-final-modal', () => ({ useModal: () => ({ open: vi.fn() }) }));

import MeetingDeliverableCard from '@/components/meeting/MeetingDeliverableCard.vue';
import { renderWithPlugins } from '@/vitest.setup';

function tileTitles(container: Element): string[] {
  return [...container.querySelectorAll('.deliverable-type-card')].map(
    (card) => card.querySelector('p')?.textContent?.trim() ?? '',
  );
}

describe('MeetingDeliverableCard', () => {
  it('renders the structured minutes tile in second position, right after the transcription', () => {
    const { container } = renderWithPlugins(MeetingDeliverableCard, {
      props: { meetingId: 1 },
    });

    expect(tileTitles(container).slice(0, 2)).toEqual(['Transcription', 'Compte-rendu structuré']);
  });

  it('always offers the custom report tile (no longer feature-flag gated)', () => {
    const { container } = renderWithPlugins(MeetingDeliverableCard, {
      props: { meetingId: 1 },
    });

    expect(tileTitles(container)).toContain('Compte-rendu personnalisé');
  });

  it('requests a STRUCTURED_MINUTES generation when its tile generate button is clicked', async () => {
    renderWithPlugins(MeetingDeliverableCard, { props: { meetingId: 1 } });

    // The transcription tile has no button, so the first "Générer" is the structured minutes tile.
    await userEvent.click(screen.getAllByRole('button', { name: 'Générer' })[0]);

    expect(createMutate).toHaveBeenCalledWith(
      expect.objectContaining({ meeting_id: 1, type: 'STRUCTURED_MINUTES' }),
      expect.anything(),
    );
  });
});
