import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/vue';
import { ref } from 'vue';
import MeetingListPage from '@/views/meeting/MeetingListPage.vue';
import { renderWithPlugins } from '@/vitest.setup';

const { mockUseFeatureFlag } = vi.hoisted(() => {
  return { mockUseFeatureFlag: vi.fn(() => ref(false)) };
});

vi.mock('@/composables/use-feature-flag', () => ({
  useFeatureFlag: () => mockUseFeatureFlag(),
}));

// MeetingsDataTable (rendered by MeetingListPageV2) calls useMeetings().getAllMeetingsQuery,
// which would otherwise fire a real HTTP request and crash on the missing Keycloak session.
vi.mock('@/services/meetings/use-meeting', async () => {
  const { mockUseMeetings } = await import('@/vitest.setup');
  return mockUseMeetings();
});

const SESSION_KEY = 'homepage-dsfr-alert-closed';
const CLOSED_ALERT_VALUE = 'CLOSED_ALERT';

describe('MeetingListPage', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it('should_display_title_and_subtitle', () => {
    renderWithPlugins(MeetingListPage);

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
    renderWithPlugins(MeetingListPage);

    expect(screen.getByText("J'importe un fichier audio ou vidéo")).toBeInTheDocument();
    expect(
      screen.getByText('Importez un fichier au format : .mp3, .wav, .m4a, .mp4, .mov.'),
    ).toBeInTheDocument();
  });

  it('should_display_record_tile', () => {
    renderWithPlugins(MeetingListPage);

    expect(screen.getByText("J'enregistre une réunion en présentiel")).toBeInTheDocument();
    expect(
      screen.getByText('Activez votre micro et parlez à tour de rôle, en direct.'),
    ).toBeInTheDocument();
  });

  it('should_display_visio_tile_without_webex', () => {
    mockUseFeatureFlag.mockReturnValue(ref(false));
    renderWithPlugins(MeetingListPage);

    expect(screen.getByText('Je participe à une réunion en visioconférence')).toBeInTheDocument();
    expect(
      screen.getByText('Ajoutez un lien ou des identifiants (Webconf, COMU, Webinaire, Visio).'),
    ).toBeInTheDocument();
  });

  it('should_display_visio_tile_with_webex', () => {
    mockUseFeatureFlag.mockReturnValue(ref(true));
    renderWithPlugins(MeetingListPage);

    expect(screen.getByText('Je participe à une réunion en visioconférence')).toBeInTheDocument();
    expect(
      screen.getByText(
        'Ajoutez un lien ou des identifiants (Webconf, COMU, Webinaire, Visio, Webex).',
      ),
    ).toBeInTheDocument();
  });

  it('should_display_second_title_and_subtitle', () => {
    renderWithPlugins(MeetingListPage);
    expect(
      screen.getByRole('heading', {
        name: 'Mes réunions MCR',
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        'Consultez les statuts des transcriptions et des comptes-rendus. Une fois la transcription disponible, générez votre compte-rendu depuis la fiche réunion, puis téléchargez vos documents.',
      ),
    ).toBeInTheDocument();
  });

  it('should_display_availability_alert', () => {
    renderWithPlugins(MeetingListPage);
    const alertInfo = screen.getByRole('alertInfo');
    expect(alertInfo).toBeInTheDocument();
  });

  it('should_hide_availability_alert_on_close', async () => {
    renderWithPlugins(MeetingListPage);
    const alertInfo = screen.getByRole('alertInfo');
    expect(alertInfo).toBeInTheDocument();
    const closeButton = within(alertInfo).getByRole('button', { name: 'Fermer le message' });
    expect(closeButton).toBeInTheDocument();
    closeButton.click();
    await nextTick();
    expect(screen.queryByRole('alertInfo')).toBeNull();
  });

  it('should_not_display_availability_alert_if_already_closed', async () => {
    sessionStorage.setItem(SESSION_KEY, CLOSED_ALERT_VALUE);
    renderWithPlugins(MeetingListPage);
    await nextTick();
    expect(screen.queryByRole('alertInfo')).toBeNull();
  });
});
