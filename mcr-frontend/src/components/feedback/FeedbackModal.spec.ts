import { i18n } from '@/plugins/i18n';
import { FEEDBACK_COMMENT_MAX_LENGTH } from '@/services/feedback/feedback.types';
import { useFeedbackDraft } from '@/services/feedback/use-feedback-draft';
import { VueQueryPlugin } from '@tanstack/vue-query';
import userEvent from '@testing-library/user-event';
import { render, screen, waitFor } from '@testing-library/vue';
import FeedbackModal from '@/components/feedback/FeedbackModal.vue';

vi.mock('vue-router', () => ({
  useRoute: () => ({ fullPath: '/meetings/1' }),
}));

function renderFeedbackModal() {
  return render(FeedbackModal, {
    global: {
      plugins: [i18n, VueQueryPlugin],
      stubs: { BaseModal: { template: '<div><slot /></div>' } },
    },
  });
}

describe('FeedbackModal', () => {
  beforeEach(() => {
    // Module-level draft state is shared across tests
    useFeedbackDraft().reset();
  });

  it('restores the draft (vote + comment) when the modal is reopened', async () => {
    // Arrange — a draft left over from a previous open/close cycle
    const draft = useFeedbackDraft();
    draft.voteType.value = 'POSITIVE';
    draft.comment.value = 'Un brouillon conservé';

    // Act — remount the modal, as vue-final-modal does on reopen
    renderFeedbackModal();

    // Assert
    const textarea = await screen.findByRole('textbox', { name: /commentaire/i });
    expect(textarea).toHaveValue('Un brouillon conservé');
  });

  it('keeps the draft in sync while the user types', async () => {
    // Arrange
    const draft = useFeedbackDraft();
    renderFeedbackModal();
    await userEvent.click(screen.getByRole('radio', { name: 'Oui' }));

    // Act
    const textarea = await screen.findByRole('textbox', { name: /commentaire/i });
    await userEvent.type(textarea, 'Super outil');

    // Assert
    expect(draft.voteType.value).toBe('POSITIVE');
    expect(draft.comment.value).toBe('Super outil');
  });

  it('shows an error and disables submit when the comment exceeds the max length', async () => {
    // Arrange — draft one character below the limit
    const draft = useFeedbackDraft();
    draft.voteType.value = 'POSITIVE';
    draft.comment.value = 'a'.repeat(FEEDBACK_COMMENT_MAX_LENGTH - 1);
    renderFeedbackModal();

    // Act — typing past the limit triggers validation
    const textarea = await screen.findByRole('textbox', { name: /commentaire/i });
    await userEvent.type(textarea, 'aa');

    // Assert
    expect(await screen.findByText(/dépasse la limite autorisée/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Envoyer' })).toBeDisabled();
  });

  it('shows no error and enables submit when the comment is at the max length', async () => {
    // Arrange
    const draft = useFeedbackDraft();
    draft.voteType.value = 'POSITIVE';
    draft.comment.value = 'a'.repeat(FEEDBACK_COMMENT_MAX_LENGTH - 1);
    renderFeedbackModal();

    // Act
    const textarea = await screen.findByRole('textbox', { name: /commentaire/i });
    await userEvent.type(textarea, 'a');

    // Assert
    expect(screen.queryByText(/dépasse la limite autorisée/i)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Envoyer' })).toBeEnabled();
  });

  it('disables submit until a vote is selected', async () => {
    // Arrange — empty draft, no vote
    renderFeedbackModal();

    // Assert — validateOnMount is async, wait for the initial validation
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Envoyer' })).toBeDisabled();
    });
  });
});
