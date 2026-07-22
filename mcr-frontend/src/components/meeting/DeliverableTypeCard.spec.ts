import { describe, it, expect, vi } from 'vitest';
import { ref } from 'vue';
import { screen } from '@testing-library/vue';

vi.mock('@/composables/use-feature-flag', () => ({
  useFeatureFlag: () => ref(true),
}));

import userEvent from '@testing-library/user-event';
import DeliverableTypeCard from '@/components/meeting/DeliverableTypeCard.vue';
import { renderWithPlugins } from '@/vitest.setup';
import type {
  DeliverableDto,
  DeliverableStatus,
  DeliverableType,
} from '@/services/deliverables/deliverables.types';

function deliverable(type: DeliverableType, status: DeliverableStatus): DeliverableDto {
  return {
    id: 42,
    meeting_id: 1,
    type,
    status,
    external_url: null,
    created_at: '2026-07-10T00:00:00Z',
    updated_at: '2026-07-10T00:00:00Z',
  };
}

describe('DeliverableTypeCard', () => {
  it('renders a generate button for a fake card and emits generate on click', async () => {
    const { emitted } = renderWithPlugins(DeliverableTypeCard, {
      props: { type: 'DECISION_RECORD' },
    });

    await userEvent.click(screen.getByRole('button', { name: 'Générer' }));

    expect(emitted().generate).toHaveLength(1);
  });

  it('shows the waiting tag and no generate button when REQUESTED', () => {
    renderWithPlugins(DeliverableTypeCard, {
      props: { type: 'DECISION_RECORD', deliverable: deliverable('DECISION_RECORD', 'REQUESTED') },
    });

    expect(screen.getByText('En attente transcription')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Générer' })).toBeNull();
  });

  it.each(['PENDING', 'IN_PROGRESS'] satisfies DeliverableStatus[])(
    'shows the in-progress tag when %s',
    (status) => {
      renderWithPlugins(DeliverableTypeCard, {
        props: { type: 'DECISION_RECORD', deliverable: deliverable('DECISION_RECORD', status) },
      });

      expect(screen.getByText('En cours')).toBeTruthy();
      expect(screen.queryByRole('button', { name: 'Générer' })).toBeNull();
    },
  );

  it('shows the download action and no generate button when AVAILABLE', () => {
    const { emitted } = renderWithPlugins(DeliverableTypeCard, {
      props: { type: 'DECISION_RECORD', deliverable: deliverable('DECISION_RECORD', 'AVAILABLE') },
    });

    const download = screen.getByRole('button', { name: 'Télécharger' });
    expect(screen.queryByRole('button', { name: 'Générer' })).toBeNull();

    return userEvent.click(download).then(() => {
      expect(emitted().download).toEqual([[42]]);
    });
  });

  it('shows an error tag and a regenerate button that emits generate when FAILED', async () => {
    const { emitted } = renderWithPlugins(DeliverableTypeCard, {
      props: { type: 'DECISION_RECORD', deliverable: deliverable('DECISION_RECORD', 'FAILED') },
    });

    expect(screen.getByText('Erreur')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Générer' })).toBeNull();

    await userEvent.click(screen.getByRole('button', { name: 'Régénérer' }));

    expect(emitted().generate).toHaveLength(1);
  });

  it('emits customize from the regenerate button of a failed custom report', async () => {
    const { emitted } = renderWithPlugins(DeliverableTypeCard, {
      props: { type: 'CUSTOM_REPORT', deliverable: deliverable('CUSTOM_REPORT', 'FAILED') },
    });

    await userEvent.click(screen.getByRole('button', { name: 'Régénérer' }));

    expect(emitted().customize).toHaveLength(1);
  });

  it('shows a transcription-failed tag and no regenerate button on a report when the transcription failed', () => {
    renderWithPlugins(DeliverableTypeCard, {
      props: { type: 'DECISION_RECORD', transcriptionFailed: true },
    });

    expect(screen.getByText('Erreur transcription')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Régénérer' })).toBeNull();
  });

  it('shows a short failed tag and no regenerate button for a failed transcription', () => {
    renderWithPlugins(DeliverableTypeCard, {
      props: { type: 'TRANSCRIPTION', deliverable: deliverable('TRANSCRIPTION', 'FAILED') },
    });

    expect(screen.getByText('Erreur')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Régénérer' })).toBeNull();
  });

  it('never shows a generate button for TRANSCRIPTION', () => {
    renderWithPlugins(DeliverableTypeCard, {
      props: { type: 'TRANSCRIPTION' },
    });

    expect(screen.queryByRole('button', { name: 'Générer' })).toBeNull();
    expect(screen.getByText('Générée automatiquement à la fin de la réunion.')).toBeTruthy();
  });

  it('offers a regenerate button that emits customize for an available custom report', async () => {
    const { emitted } = renderWithPlugins(DeliverableTypeCard, {
      props: { type: 'CUSTOM_REPORT', deliverable: deliverable('CUSTOM_REPORT', 'AVAILABLE') },
    });

    await userEvent.click(screen.getByRole('button', { name: 'Régénérer' }));

    expect(emitted().customize).toHaveLength(1);
  });

  it('does not offer a regenerate button for a standard available report', () => {
    renderWithPlugins(DeliverableTypeCard, {
      props: { type: 'DECISION_RECORD', deliverable: deliverable('DECISION_RECORD', 'AVAILABLE') },
    });

    expect(screen.queryByRole('button', { name: 'Régénérer' })).toBeNull();
  });

  it('emits customize for a custom card', async () => {
    const { emitted } = renderWithPlugins(DeliverableTypeCard, {
      props: { type: 'CUSTOM_REPORT' },
    });

    await userEvent.click(screen.getByRole('button', { name: 'Personnaliser' }));

    expect(emitted().customize).toHaveLength(1);
  });

  it('shows the waiting tag optimistically while the transcription is not ready', () => {
    renderWithPlugins(DeliverableTypeCard, {
      props: { type: 'DECISION_RECORD', isGenerating: true, transcriptionReady: false },
    });

    expect(screen.getByText('En attente transcription')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Générer' })).toBeNull();
  });

  it('shows the in-progress tag optimistically once the transcription is ready', () => {
    renderWithPlugins(DeliverableTypeCard, {
      props: { type: 'DECISION_RECORD', isGenerating: true, transcriptionReady: true },
    });

    expect(screen.getByText('En cours')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Générer' })).toBeNull();
  });
});
