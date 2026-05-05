import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/vue';
import VisioRecordingCard from '@/components/meeting/VisioRecordingCard.vue';
import { renderWithPlugins } from '@/vitest.setup';

vi.mock('@/services/meetings/use-meeting', () => ({
  useMeetings: () => ({
    startCaptureMutation: () => ({
      mutate: vi.fn(),
      isPending: { value: false },
    }),
    stopCaptureMutation: () => ({
      mutate: vi.fn(),
      isPending: { value: false },
    }),
  }),
}));

vi.mock('vue-timer-hook', () => ({
  useStopwatch: () => ({
    hours: { value: 0 },
    minutes: { value: 0 },
    seconds: { value: 0 },
  }),
}));

describe('VisioRecordingCard', () => {
  it.each(['CAPTURE_PENDING', 'CAPTURE_BOT_IS_CONNECTING'] as const)(
    'should display VisioConnecting for status %s',
    (status) => {
      renderWithPlugins(VisioRecordingCard, {
        props: { meetingId: 1, status, startDate: undefined },
      });

      expect(screen.getByText('CONNEXION EN COURS DE MCR AGENT')).toBeTruthy();
      expect(
        screen.getByText('Merci de patienter, cela peut prendre quelques instants.'),
      ).toBeTruthy();
    },
  );

  it('should display VisioInProgress for status CAPTURE_IN_PROGRESS', () => {
    renderWithPlugins(VisioRecordingCard, {
      props: {
        meetingId: 1,
        status: 'CAPTURE_IN_PROGRESS',
        startDate: new Date().toISOString(),
      },
    });

    expect(screen.getByText("EN COURS D'ENREGISTREMENT")).toBeTruthy();
  });

  it.each(['CAPTURE_FAILED', 'CAPTURE_BOT_CONNECTION_FAILED'] as const)(
    'should display VisioError for status %s',
    (status) => {
      renderWithPlugins(VisioRecordingCard, {
        props: { meetingId: 1, status, startDate: undefined },
      });

      expect(screen.getByText('ERREUR')).toBeTruthy();
      expect(screen.getByText('La connexion de MCR Agent à la réunion a échoué.')).toBeTruthy();
      expect(screen.getByText('Relancer la connexion')).toBeTruthy();
    },
  );

  it('should render nothing for an unrelated status', () => {
    const { container } = renderWithPlugins(VisioRecordingCard, {
      props: { meetingId: 1, status: 'NONE', startDate: undefined },
    });

    expect(container.textContent).toBe('');
  });
});
