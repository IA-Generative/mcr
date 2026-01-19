import { describe, it, expect, vi, beforeEach } from 'vitest';
import TableHeaderActions from '@/components/meeting/table/TableHeaderActions.vue';
import { renderWithPlugins } from '@/vitest.setup';

// Mock du composable useToaster
const { mockAddErrorMessage } = vi.hoisted(() => ({
  mockAddErrorMessage: vi.fn(),
}));

// Mock du composable useFeatureFlag
vi.mock('@/composables/use-feature-flag', () => ({
  useFeatureFlag: () => ({ value: true }),
}));

vi.mock('@/composables/use-toaster', () => ({
  default: () => ({
    addErrorMessage: mockAddErrorMessage,
  }),
}));

// Mock du service des meetings
const mockCreateMeeting = vi.fn();
const mockImportMeeting = vi.fn();
const mockStartTranscription = vi.fn();

vi.mock('@/services/meetings/use-meeting', () => ({
  useMeetings: () => ({
    addMeetingMutation: () => ({
      mutate: mockCreateMeeting,
    }),
    importMeetingMutation: () => ({
      mutate: mockImportMeeting,
      isPending: { value: false },
    }),
    startTranscriptionMutation: () => ({
      mutate: mockStartTranscription,
    }),
  }),
}));

// Mock de vue-router
const mockPush = vi.fn();
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

// Mock de vue-final-modal
vi.mock('vue-final-modal', () => ({
  useModal: () => ({
    open: vi.fn(),
    close: vi.fn(),
  }),
}));

describe('TableHeaderActions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should_display_error_toaster_when_meeting_creation_fails', async () => {
    // Arrange
    const mockError = new Error('Erreur 500');
    mockCreateMeeting.mockImplementation((_values, options) => {
      options.onError(mockError);
    });

    // Act
    renderWithPlugins(TableHeaderActions);

    // Simuler l'appel de création de réunion
    const testMeetingData = {
      name: 'Test Meeting',
      meeting_platform_id: '12345',
    };

    mockCreateMeeting(testMeetingData, {
      onSuccess: vi.fn(),
      onError: () => {
        mockAddErrorMessage('Erreur lors de la création de la réunion');
      },
    });

    // Assert
    expect(mockAddErrorMessage).toHaveBeenCalledWith('Erreur lors de la création de la réunion');
  });

  it('should_not_display_error_toaster_when_meeting_creation_succeeds', async () => {
    // Arrange
    mockCreateMeeting.mockImplementation((_values, options) => {
      options.onSuccess({ id: 1 });
    });

    // Act
    renderWithPlugins(TableHeaderActions);

    // Simuler l'appel de création de réunion réussie
    const testMeetingData = {
      name: 'Test Meeting',
      meeting_platform_id: '12345',
    };

    mockCreateMeeting(testMeetingData, {
      onSuccess: vi.fn(),
      onError: vi.fn(),
    });

    // Assert
    expect(mockAddErrorMessage).not.toHaveBeenCalled();
  });

  it('should_display_file_upload_error_toaster_when_import_meeting_fails_with_general_error', async () => {
    // Arrange
    const mockError = new Error('Erreur S3');
    mockImportMeeting.mockImplementation((_values, options) => {
      options.onError(mockError);
    });

    // Act
    renderWithPlugins(TableHeaderActions);

    // Simuler l'appel d'import de meeting avec erreur générale
    const testImportData = {
      dto: { name: 'Test Meeting', creation_date: '2024-01-01' },
      file: new File(['test'], 'test.mp3', { type: 'audio/mp3' }),
    };

    mockImportMeeting(testImportData, {
      onSuccess: vi.fn(),
      onError: (error: any) => {
        if (error.message === 'Erreur S3') {
          mockAddErrorMessage("Erreur lors de l'envoi du fichier. Veuillez réessayer.");
        }
      },
    });

    // Assert
    expect(mockAddErrorMessage).toHaveBeenCalledWith(
      "Erreur lors de l'envoi du fichier. Veuillez réessayer.",
    );
  });

  it('should_display_unsupported_format_error_toaster_when_import_meeting_fails_with_415_error', async () => {
    // Arrange
    const mockAxiosError = {
      response: { status: 415 },
      message: 'Unsupported Media Type',
    };
    mockImportMeeting.mockImplementation((_values, options) => {
      options.onError(mockAxiosError);
    });

    // Act
    renderWithPlugins(TableHeaderActions);

    // Simuler l'appel d'import de meeting avec erreur 415
    const testImportData = {
      dto: { name: 'Test Meeting', creation_date: '2024-01-01' },
      file: new File(['test'], 'test.xyz', { type: 'application/xyz' }),
    };

    mockImportMeeting(testImportData, {
      onSuccess: vi.fn(),
      onError: (error: any) => {
        if (error.response?.status === 415) {
          mockAddErrorMessage("Désolé, ce format de fichier n'est pas encore supporté par FCR.");
        }
      },
    });

    // Assert
    expect(mockAddErrorMessage).toHaveBeenCalledWith(
      "Désolé, ce format de fichier n'est pas encore supporté par FCR.",
    );
  });
});
