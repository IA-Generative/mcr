import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/vue';
import { ref } from 'vue';
import MeetingListPageV2 from '@/views/meeting/MeetingListPageV2.vue';
import { renderWithPlugins } from '@/vitest.setup';

const mockUseFeatureFlag = vi.fn(() => ref(false));

vi.mock('@/composables/use-feature-flag', () => ({
  useFeatureFlag: () => mockUseFeatureFlag(),
}));

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

  it('should_display_import_tile', () => {
    renderWithPlugins(MeetingListPageV2);

    expect(screen.getByText("J'importe un fichier audio ou vidéo")).toBeInTheDocument();
    expect(
      screen.getByText('Importez un fichier au format : .mp3, .wav, .m4a, .mp4, .mov.'),
    ).toBeInTheDocument();
  });

  it('should_display_record_tile', () => {
    renderWithPlugins(MeetingListPageV2);

    expect(screen.getByText("J'enregistre une réunion en présentiel")).toBeInTheDocument();
    expect(
      screen.getByText('Activez votre micro et parlez à tour de rôle, en direct.'),
    ).toBeInTheDocument();
  });

  it('should_display_visio_tile_without_webex', () => {
    mockUseFeatureFlag.mockReturnValue(ref(false));
    renderWithPlugins(MeetingListPageV2);

    expect(screen.getByText('Je participe à une réunion en visioconférence')).toBeInTheDocument();
    expect(
      screen.getByText('Ajoutez un lien ou des identifiants (Webconf, COMU, Webinaire, Visio).'),
    ).toBeInTheDocument();
  });

  it('should_display_visio_tile_with_webex', () => {
    mockUseFeatureFlag.mockReturnValue(ref(true));
    renderWithPlugins(MeetingListPageV2);

    expect(screen.getByText('Je participe à une réunion en visioconférence')).toBeInTheDocument();
    expect(
      screen.getByText(
        'Ajoutez un lien ou des identifiants (Webconf, COMU, Webinaire, Visio, Webex).',
      ),
    ).toBeInTheDocument();
  });
});
