import { i18n } from '@/plugins/i18n';
import { VueQueryPlugin } from '@tanstack/vue-query';
import { render, screen } from '@testing-library/vue';
import FeedbackModal from '@/components/feedback/FeedbackModal.vue';
import { FEEDBACK_COMMENT_MAX_LENGTH } from '@/services/feedback/feedback.types';

vi.mock('vue-router', () => ({
  useRoute: () => ({ fullPath: '/meetings/1' }),
}));

function renderFeedbackModal(comment: string) {
  return render(FeedbackModal, {
    props: {
      selectedVote: 'POSITIVE' as const,
      comment,
      onSelectVote: vi.fn(),
      onUpdateComment: vi.fn(),
      onSuccess: vi.fn(),
      onError: vi.fn(),
    },
    global: {
      plugins: [i18n, VueQueryPlugin],
      stubs: { BaseModal: { template: '<div><slot /></div>' } },
    },
  });
}

describe('FeedbackModal', () => {
  it('shows an error and disables submit when the comment exceeds the max length', () => {
    // Arrange
    renderFeedbackModal('a'.repeat(FEEDBACK_COMMENT_MAX_LENGTH + 1));

    // Assert
    expect(screen.getByText(/dépasse la limite autorisée/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Envoyer' })).toBeDisabled();
  });

  it('shows no error and enables submit when the comment is at the max length', () => {
    // Arrange
    renderFeedbackModal('a'.repeat(FEEDBACK_COMMENT_MAX_LENGTH));

    // Assert
    expect(screen.queryByText(/dépasse la limite autorisée/i)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Envoyer' })).toBeEnabled();
  });
});
