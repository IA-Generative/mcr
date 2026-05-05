import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/vue';
import RecordingCard from '@/components/meeting/RecordingCard.vue';
import { renderWithPlugins } from '@/vitest.setup';

vi.mock('@/composables/use-recording-session', () => ({
  useRecordingSession: () => ({
    time: { hours: { value: 0 }, minutes: { value: 0 }, seconds: { value: 0 } },
    isRecording: { value: true },
    isInactive: { value: false },
    isSendingLastAudioChunks: { value: false },
    audioInputLevel: { value: 0 },
    effectiveOffline: { value: false },
    statusLabel: { value: 'En cours' },
    pauseRecording: vi.fn(),
    resumeRecording: vi.fn(),
    stopRecording: vi.fn(),
  }),
}));

vi.mock('@/composables/use-leave-guard', () => ({
  useLeaveGuard: vi.fn(),
}));

vi.mock('@/services/meetings/use-meeting', () => ({
  useMeetings: () => ({
    startCaptureMutation: () => ({
      mutate: vi.fn(),
      isPending: { value: false },
    }),
  }),
}));

vi.mock('vue-final-modal', () => ({
  useModal: () => ({
    open: vi.fn(),
  }),
}));

vi.mock('vue-timer-hook', () => ({
  useStopwatch: () => ({
    hours: { value: 0 },
    minutes: { value: 0 },
    seconds: { value: 0 },
  }),
}));

describe('RecordingCard', () => {
  it('should display the recording title', () => {
    renderWithPlugins(RecordingCard, {
      props: {
        meetingId: 1,
        status: 'CAPTURE_IN_PROGRESS',
        namePlatform: 'MCR_RECORD',
        startDate: undefined,
      },
    });

    expect(screen.getByText('Enregistrement')).toBeTruthy();
  });

  it('should display advices link for MCR_RECORD platform', () => {
    renderWithPlugins(RecordingCard, {
      props: {
        meetingId: 1,
        status: 'CAPTURE_IN_PROGRESS',
        namePlatform: 'MCR_RECORD',
        startDate: undefined,
      },
    });

    expect(screen.getByRole('link', { name: /conseils/ })).toBeTruthy();
  });

  it('should display VisioRecordingCard for online platform', () => {
    renderWithPlugins(RecordingCard, {
      props: {
        meetingId: 1,
        status: 'CAPTURE_PENDING',
        namePlatform: 'COMU',
        startDate: undefined,
      },
    });

    expect(screen.getByText('CONNEXION EN COURS DE MCR AGENT')).toBeTruthy();
  });

  it('should display visio advices link for online platform', () => {
    renderWithPlugins(RecordingCard, {
      props: {
        meetingId: 1,
        status: 'CAPTURE_PENDING',
        namePlatform: 'COMU',
        startDate: undefined,
      },
    });

    expect(screen.getByRole('link', { name: /conseils/ })).toBeTruthy();
  });
});
