import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ref } from 'vue';
import { screen } from '@testing-library/vue';
import MeetingListPage from '@/views/meeting/MeetingListPage.vue';
import { renderWithPlugins } from '@/vitest.setup';

// Utilisation de vi.hoisted pour déclarer les mocks avant le hoisting
const { mockGetAllMeetingsQuery, mockUseQuery, mockFormatDurationMinutes, mockAddErrorMessage } =
  vi.hoisted(() => {
    return {
      mockGetAllMeetingsQuery: vi.fn(),
      mockUseQuery: vi.fn(),
      mockFormatDurationMinutes: vi.fn(),
      mockAddErrorMessage: vi.fn(),
    };
  });

// Mock du composable useToaster
vi.mock('@/composables/use-toaster', () => ({
  default: () => ({
    addErrorMessage: mockAddErrorMessage,
  }),
}));

// Mock du service des meetings
vi.mock('@/services/meetings/use-meeting', () => ({
  useMeetings: () => ({
    getAllMeetingsQuery: mockGetAllMeetingsQuery,
  }),
}));

// Mock de useQuery pour le temps d'attente global
vi.mock('@tanstack/vue-query', () => ({
  useQuery: mockUseQuery,
}));

// Mock de formatDurationMinutes
vi.mock('@/utils/timeFormatting', () => ({
  formatDurationMinutes: mockFormatDurationMinutes,
}));

describe('MeetingListPage - 24h warning banner', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockGetAllMeetingsQuery.mockReturnValue({
      data: ref([]),
      isLoading: ref(false),
      error: ref(null),
    });

    mockFormatDurationMinutes.mockReturnValue('25h');
  });

  it('should_display_warning_banner_when_waiting_time_greater_or_equal_to_24_hours', () => {
    // Arrange
    mockUseQuery.mockReturnValue({
      data: ref({ estimation_duration_minutes: 25 * 60 }), // 25 heures
    });

    // Act
    renderWithPlugins(MeetingListPage);

    // Assert
    expect(screen.getByText('Délai de traitement prolongé')).toBeInTheDocument();
    expect(screen.getByText('25h')).toBeInTheDocument();
  });

  it('should_not_display_warning_banner_when_waiting_time_less_than_24_hours', () => {
    // Arrange
    mockUseQuery.mockReturnValue({
      data: ref({ estimation_duration_minutes: 12 * 60 }), // 12 heures
    });

    // Act
    renderWithPlugins(MeetingListPage);

    // Assert
    expect(screen.queryByText('Délai de traitement prolongé')).not.toBeInTheDocument();
  });
});
