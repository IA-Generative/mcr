import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/vue';
import MeetingListPageV2 from '@/views/meeting/MeetingListPageV2.vue';
import { renderWithPlugins } from '@/vitest.setup';

describe('MeetingListPage v2', () => {
  it('should_display_title_and_subtitle', () => {
    renderWithPlugins(MeetingListPageV2);

    expect(
      screen.getByRole('heading', {
        name: 'Faire un compte-rendu',
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        'Simplifiez vos réunions : enregistrez, récupérez la transcription, puis générez un compte-rendu (relevé de décisions, synthèse courte ou détaillée).',
      ),
    ).toBeInTheDocument();
  });
});
