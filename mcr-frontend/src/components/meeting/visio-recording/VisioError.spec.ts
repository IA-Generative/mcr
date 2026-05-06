import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/vue';
import { fireEvent } from '@testing-library/vue';
import VisioError from '@/components/meeting/visio-recording/VisioError.vue';
import { renderWithPlugins } from '@/vitest.setup';

const mockStartCapture = vi.fn();

vi.mock('@/services/meetings/use-meeting', () => ({
  useMeetings: () => ({
    startCaptureMutation: () => ({
      mutate: mockStartCapture,
      isPending: { value: false },
    }),
  }),
}));

describe('VisioError', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should display the retry button', () => {
    renderWithPlugins(VisioError, {
      props: { meetingId: 42 },
    });

    expect(screen.getByText('Relancer la connexion')).toBeTruthy();
  });

  it('should call startCaptureMutation with meetingId on retry click', async () => {
    renderWithPlugins(VisioError, {
      props: { meetingId: 42 },
    });

    await fireEvent.click(screen.getByText('Relancer la connexion'));

    expect(mockStartCapture).toHaveBeenCalledWith(42);
  });
});
