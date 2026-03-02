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

// MeetingListPage renders child components that each use different parts of useMeetings().
// mockUseMeetings uses a Proxy so any unspecified property returns a default mock mutation,
// avoiding the need to explicitly mock every mutation used by every child component.
vi.mock('@/services/meetings/use-meeting', async () => {
  const { mockUseMeetings } = await import('@/vitest.setup');
  return mockUseMeetings({ getAllMeetingsQuery: mockGetAllMeetingsQuery });
});

vi.mock('@/composables/use-toaster', () => ({
  default: () => ({
    addErrorMessage: mockAddErrorMessage,
  }),
}));

// Mock de useQuery pour le temps d'attente global
vi.mock('@tanstack/vue-query', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@tanstack/vue-query')>()),
  useQuery: mockUseQuery,
}));

// Mock de formatDurationMinutes
vi.mock('@/utils/timeFormatting', () => ({
  formatDurationMinutes: mockFormatDurationMinutes,
}));

// Mock de useFeatureFlag pour éviter l'initialisation d'Unleash au niveau module
vi.mock('@/composables/use-feature-flag', () => ({
  useFeatureFlag: () => ref(false),
}));

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ params: {} }),
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
