import { screen, waitFor } from '@testing-library/vue';
import userEvent from '@testing-library/user-event';
import { renderWithPlugins } from '@/vitest.setup';
import type { DeliverableDto } from '@/services/deliverables/deliverables.types';

const { open, close, upsert, remove, addErrorMessage, addSuccessMessage } = vi.hoisted(() => ({
  open: vi.fn(),
  close: vi.fn(),
  upsert: vi.fn(),
  remove: vi.fn(),
  addErrorMessage: vi.fn(),
  addSuccessMessage: vi.fn(),
}));

vi.mock('vue-final-modal', () => ({
  useModal: vi.fn(() => ({ open, close })),
  useVfm: () => ({ close }),
  VueFinalModal: { template: '<div><slot /></div>' },
}));

vi.mock('@/services/deliverable-feedback/deliverable-feedback.service', () => ({
  upsertDeliverableFeedback: (...args: unknown[]) => upsert(...args),
  deleteDeliverableFeedback: (...args: unknown[]) => remove(...args),
}));

vi.mock('@/composables/use-toaster', () => ({
  default: () => ({ addErrorMessage, addSuccessMessage }),
}));

import { useModal } from 'vue-final-modal';
import DeliverableFeedbackThumbs from './DeliverableFeedbackThumbs.vue';

function deliverable(feedback: DeliverableDto['feedback'] = null): DeliverableDto {
  return {
    id: 42,
    meeting_id: 1,
    type: 'DECISION_RECORD',
    status: 'AVAILABLE',
    external_url: null,
    created_at: '2026-07-10T00:00:00Z',
    updated_at: '2026-07-10T00:00:00Z',
    feedback,
  };
}

function renderThumbs(feedback: DeliverableDto['feedback'] = null) {
  return renderWithPlugins(DeliverableFeedbackThumbs, {
    props: { deliverable: deliverable(feedback) },
  });
}

function submitFromModal(comment: string) {
  const { attrs } = vi.mocked(useModal).mock.calls[0][0] as {
    attrs: { onSubmit: (comment: string) => void };
  };
  attrs.onSubmit(comment);
}

function thumbUp() {
  return screen.getByRole('button', { name: /utile/i });
}

describe('DeliverableFeedbackThumbs', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    remove.mockResolvedValue(undefined);
  });

  it('shows no vote and records nothing until the modal is submitted', async () => {
    renderThumbs();

    await userEvent.click(thumbUp());

    expect(open).toHaveBeenCalled();
    expect(upsert).not.toHaveBeenCalled();
    expect(remove).not.toHaveBeenCalled();
  });

  it('shows the vote as cast when a positive feedback exists', () => {
    renderThumbs({ vote_type: 'POSITIVE', comment: null });

    expect(thumbUp()).toHaveAttribute('aria-pressed', 'true');
  });

  it('retracts an existing vote without opening the modal', async () => {
    renderThumbs({ vote_type: 'POSITIVE', comment: 'bien' });

    await userEvent.click(thumbUp());

    await waitFor(() => expect(remove).toHaveBeenCalledWith(42));
    expect(open).not.toHaveBeenCalled();
  });

  it('confirms a retraction with the emptied thumb alone, never a success banner', async () => {
    renderThumbs({ vote_type: 'POSITIVE', comment: 'bien' });

    await userEvent.click(thumbUp());

    await waitFor(() => expect(remove).toHaveBeenCalled());
    expect(addSuccessMessage).not.toHaveBeenCalled();
  });

  it('warns the user when the retraction fails', async () => {
    remove.mockRejectedValue(new Error('boom'));
    renderThumbs({ vote_type: 'POSITIVE', comment: 'bien' });

    await userEvent.click(thumbUp());

    await waitFor(() => expect(addErrorMessage).toHaveBeenCalled());
  });

  it('closes the modal and thanks the user once the vote is recorded', async () => {
    upsert.mockResolvedValue({ vote_type: 'POSITIVE', comment: null });
    renderThumbs();
    await userEvent.click(thumbUp());

    submitFromModal('clair et fidèle');

    await waitFor(() => expect(addSuccessMessage).toHaveBeenCalled());
    expect(close).toHaveBeenCalled();
  });

  it('keeps the modal open and warns the user when the vote cannot be saved', async () => {
    upsert.mockRejectedValue(new Error('boom'));
    renderThumbs();
    await userEvent.click(thumbUp());

    submitFromModal('un long retour');

    await waitFor(() => expect(addErrorMessage).toHaveBeenCalled());
    expect(close).not.toHaveBeenCalled();
    expect(addSuccessMessage).not.toHaveBeenCalled();
  });

  it('drops a blank comment rather than sending whitespace', async () => {
    upsert.mockResolvedValue({ vote_type: 'POSITIVE', comment: null });
    renderThumbs();
    await userEvent.click(thumbUp());

    submitFromModal('   ');

    await waitFor(() => expect(upsert).toHaveBeenCalledWith(42, { vote_type: 'POSITIVE' }));
  });
});
