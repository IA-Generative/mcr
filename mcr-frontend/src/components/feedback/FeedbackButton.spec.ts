import FeedbackButton from '@/components/feedback/FeedbackButton.vue';
import FeedbackModal from '@/components/feedback/FeedbackModal.vue';
import { renderWithPlugins } from '@/vitest.setup';
import userEvent from '@testing-library/user-event';
import { screen } from '@testing-library/vue';
import { describe, expect, it, vi } from 'vitest';

const { openModal, useModal } = vi.hoisted(() => ({
  openModal: vi.fn(),
  useModal: vi.fn(() => ({ open: openModal })),
}));

vi.mock('vue-final-modal', () => ({ useModal }));

describe('FeedbackButton', () => {
  it('shows its label alongside the pictogram by default', () => {
    renderWithPlugins(FeedbackButton);

    const button = screen.getByRole('button', { name: 'Faire un retour' });
    expect(button).not.toHaveClass('trigger--compact');
    expect(screen.getByText('Faire un retour')).toBeInTheDocument();
  });

  it('compacts to a circle but keeps its accessible name when the import sticky is open', () => {
    renderWithPlugins(FeedbackButton, { props: { compact: true } });

    expect(screen.getByRole('button', { name: 'Faire un retour' })).toHaveClass('trigger--compact');
  });

  it.each([false, true])('opens the feedback modal on click (compact: %s)', async (compact) => {
    renderWithPlugins(FeedbackButton, { props: { compact } });

    await userEvent.click(screen.getByRole('button', { name: 'Faire un retour' }));

    expect(useModal).toHaveBeenCalledWith({ component: FeedbackModal });
    expect(openModal).toHaveBeenCalled();
  });
});
