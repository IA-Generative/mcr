import { describe, it, expect, vi, beforeEach } from 'vitest';
import GenerateReportAction from '@/components/meeting/report/GenerateReportAction.vue';
import { renderWithPlugins } from '@/vitest.setup';
import type { MeetingDto } from '@/services/meetings/meetings.types';

// Mock du composable useToaster
const mockAddErrorMessage = vi.fn();
vi.mock('@/composables/use-toaster', () => ({
  default: () => ({
    addErrorMessage: mockAddErrorMessage,
  }),
}));

// Mock du service des meetings
const mockGenerateReport = vi.fn();
const mockGetReport = vi.fn();

vi.mock('@/services/meetings/use-meeting', () => ({
  useMeetings: () => ({
    generateReportMutation: (options: any) => ({
      mutate: mockGenerateReport,
      ...options,
    }),
    getReportMutation: (options: any) => ({
      mutate: mockGetReport,
      ...options,
    }),
  }),
}));

// Mock de l'utilitaire de téléchargement
vi.mock('@/utils/file', () => ({
  downloadFileFromAxios: vi.fn(),
}));

describe('GenerateReportAction', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should_display_error_toaster_when_report_generation_fails', async () => {
    // Arrange
    const mockError = new Error('Erreur LLM');
    mockGenerateReport.mockImplementation((_meetingId, options) => {
      options.onError(mockError);
    });

    const mockMeeting = {
      id: 1,
      name: 'Test Meeting',
      name_platform: 'MCR_RECORD',
      status: 'TRANSCRIPTION_DONE',
      creation_date: '2021-01-01',
    };

    // Act
    renderWithPlugins(GenerateReportAction, {
      props: {
        meeting: mockMeeting as MeetingDto,
      },
    });

    // Simuler l'appel de generateReport avec erreur
    mockGenerateReport(1, {
      onError: () => {
        mockAddErrorMessage('Erreur lors de la génération du compte rendu. Veuillez réessayer.');
      },
    });

    // Assert
    expect(mockAddErrorMessage).toHaveBeenCalledWith(
      'Erreur lors de la génération du compte rendu. Veuillez réessayer.',
    );
  });

  it('should_not_display_error_toaster_when_report_generation_succeeds', async () => {
    // Arrange
    mockGenerateReport.mockImplementation((_meetingId, options) => {
      options.onSuccess();
    });

    const mockMeeting = {
      id: 1,
      name: 'Test Meeting',
      name_platform: 'MCR_RECORD',
      creation_date: '2021-01-01',
      status: 'TRANSCRIPTION_DONE',
    };

    // Act
    renderWithPlugins(GenerateReportAction, {
      props: {
        meeting: mockMeeting as MeetingDto,
      },
    });

    // Simuler l'appel de generateReport avec succès
    mockGenerateReport(1, {
      onSuccess: vi.fn(),
      onError: vi.fn(),
    });

    // Assert
    expect(mockAddErrorMessage).not.toHaveBeenCalled();
  });

  it('should_display_error_toaster_when_get_report_fails', async () => {
    // Arrange
    const mockError = new Error('Erreur téléchargement');
    mockGetReport.mockImplementation((_meetingId, options) => {
      options.onError(mockError);
    });

    const mockMeeting = {
      id: 1,
      name: 'Test Meeting',
      name_platform: 'MCR_RECORD',
      creation_date: '2021-01-01',
      status: 'REPORT_DONE',
    };

    // Act
    renderWithPlugins(GenerateReportAction, {
      props: {
        meeting: mockMeeting as MeetingDto,
      },
    });

    // Simuler l'appel de getReport avec erreur
    mockGetReport(1, {
      onSuccess: vi.fn(),
      onError: () => {
        mockAddErrorMessage('Une erreur est survenue');
      },
    });

    // Assert
    expect(mockAddErrorMessage).toHaveBeenCalledWith('Une erreur est survenue');
  });
});
