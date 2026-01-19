import { describe, it, expect, vi, beforeEach } from 'vitest';
import TranscriptionNone from '@/components/meeting/transcription/states/TranscriptionNone.vue';
import { renderWithPlugins } from '@/vitest.setup';

// Mock du composable useToaster
const mockAddErrorMessage = vi.fn();
vi.mock('@/composables/use-toaster', () => ({
  default: () => ({
    addErrorMessage: mockAddErrorMessage,
  }),
}));

// Mock du service des meetings
const mockStartCapture = vi.fn();
vi.mock('@/services/meetings/use-meeting', () => ({
  useMeetings: () => ({
    startCaptureMutation: () => ({
      mutate: mockStartCapture,
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

describe('TranscriptionNone', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should_display_error_toaster_when_start_capture_fails', async () => {
    // Arrange
    const mockError = new Error('Erreur 500');
    mockStartCapture.mockImplementation((_meetingId, options) => {
      options.onError(mockError);
    });

    // Act
    renderWithPlugins(TranscriptionNone, {
      props: {
        meetingId: 1,
      },
    });

    // Simuler l'appel de startCapture avec erreur
    mockStartCapture(1, {
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

  it('should_not_display_error_toaster_when_start_capture_succeeds', async () => {
    // Arrange
    mockStartCapture.mockImplementation((_meetingId, options) => {
      options.onSuccess();
    });

    // Act
    renderWithPlugins(TranscriptionNone, {
      props: {
        meetingId: 1,
      },
    });

    // Simuler l'appel de startCapture avec succès
    mockStartCapture(1, {
      onSuccess: vi.fn(),
      onError: vi.fn(),
    });

    // Assert
    expect(mockAddErrorMessage).not.toHaveBeenCalled();
  });
});
