import { describe, it, expect, vi, beforeEach } from 'vitest';
import TranscriptionInProgress from '@/components/meeting/transcription/states/TranscriptionInProgress.vue';
import { renderWithPlugins } from '@/vitest.setup';

// Mock du composable useToaster
const mockAddErrorMessage = vi.fn();
vi.mock('@/composables/use-toaster', () => ({
  default: () => ({
    addErrorMessage: mockAddErrorMessage,
  }),
}));

// Mock du service des meetings
const mockStopCapture = vi.fn();
vi.mock('@/services/meetings/use-meeting', () => ({
  useMeetings: () => ({
    stopCaptureMutation: () => ({
      mutate: mockStopCapture,
      isPending: { value: false },
    }),
  }),
}));

// Mock de vue-final-modal
vi.mock('vue-final-modal', () => ({
  useModal: () => ({
    open: vi.fn(),
  }),
}));

describe('TranscriptionInProgress', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should_display_error_toaster_when_stop_capture_fails', async () => {
    // Arrange
    const mockError = new Error('Erreur 500');
    mockStopCapture.mockImplementation((_meetingId, options) => {
      options.onError(mockError);
    });

    // Act
    renderWithPlugins(TranscriptionInProgress, {
      props: {
        meetingId: 1,
      },
    });

    // Simuler l'appel de stopCapture avec erreur
    mockStopCapture(1, {
      onSuccess: vi.fn(),
      onError: () => {
        mockAddErrorMessage('Erreur lors de la captation audio de la visioconférence');
      },
    });

    // Assert
    expect(mockAddErrorMessage).toHaveBeenCalledWith(
      'Erreur lors de la captation audio de la visioconférence',
    );
  });

  it('should_not_display_error_toaster_when_stop_capture_succeeds', async () => {
    // Arrange
    mockStopCapture.mockImplementation((_meetingId, options) => {
      options.onSuccess();
    });

    // Act
    renderWithPlugins(TranscriptionInProgress, {
      props: {
        meetingId: 1,
      },
    });

    // Simuler l'appel de stopCapture avec succès
    mockStopCapture(1, {
      onSuccess: vi.fn(),
      onError: vi.fn(),
    });

    // Assert
    expect(mockAddErrorMessage).not.toHaveBeenCalled();
  });
});
