import { screen } from '@testing-library/vue';
import userEvent from '@testing-library/user-event';
import { renderWithPlugins } from '@/vitest.setup';

vi.mock('vue-final-modal', () => ({
  useVfm: () => ({ close: vi.fn() }),
  VueFinalModal: { template: '<div><slot /></div>' },
}));

vi.mock('@/components/core/BaseModal.vue', () => ({
  default: {
    template: '<div><slot /><slot name="footer" /></div>',
    props: ['modalId', 'title', 'size', 'noActions', 'disableCloseOnOutsideClick'],
  },
}));

import DeliverableFeedbackModal from './DeliverableFeedbackModal.vue';

function renderModal(props: Record<string, unknown> = {}) {
  const onSubmit = vi.fn();
  const { rerender } = renderWithPlugins(DeliverableFeedbackModal, {
    props: { isSubmitting: false, onSubmit, ...props },
  });
  return { rerender, onSubmit };
}

function commentBox() {
  return screen.getByRole('textbox');
}

function submitButton() {
  return screen.getByRole('button', { name: /envoyer/i });
}

describe('DeliverableFeedbackModal', () => {
  it('opens blank', () => {
    renderModal();

    expect(commentBox()).toHaveValue('');
  });

  it('submits without a comment, because the comment is optional', async () => {
    const { onSubmit } = renderModal();

    await userEvent.click(submitButton());

    expect(onSubmit).toHaveBeenCalledWith('');
  });

  it('submits the comment the user wrote', async () => {
    const { onSubmit } = renderModal();

    await userEvent.type(commentBox(), 'clair et fidèle');
    await userEvent.click(submitButton());

    expect(onSubmit).toHaveBeenCalledWith('clair et fidèle');
  });

  it('keeps the comment on screen while the submission is in flight', async () => {
    const { rerender } = renderModal();
    await userEvent.type(commentBox(), 'un long retour');

    await rerender({ isSubmitting: true });

    expect(commentBox()).toHaveValue('un long retour');
    expect(submitButton()).toBeDisabled();
  });

  it('does not submit twice while a submission is in flight', async () => {
    const { onSubmit } = renderModal({ isSubmitting: true });

    await userEvent.click(submitButton());

    expect(onSubmit).not.toHaveBeenCalled();
  });
});
