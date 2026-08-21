import { nextTick } from 'vue';
import { screen, waitFor } from '@testing-library/vue';
import userEvent from '@testing-library/user-event';
import { renderWithPlugins } from '@/vitest.setup';
import type { DeliverableDto } from '@/services/deliverables/deliverables.types';
import type { NegativeFeedbackDraft } from './DeliverableNegativeFeedbackModal.vue';

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
  getDeliverableFeedbackReasons: vi.fn(),
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

function modalAttrs(index: number) {
  return vi.mocked(useModal).mock.calls[index][0] as unknown as {
    attrs: { onSubmit: unknown; onClosed: () => void };
  };
}

function submitPositiveModal(comment: string) {
  (modalAttrs(0).attrs.onSubmit as (comment: string) => void)(comment);
}

function submitNegativeModal(draft: NegativeFeedbackDraft) {
  (modalAttrs(1).attrs.onSubmit as (draft: NegativeFeedbackDraft) => void)(draft);
}

function dismissNegativeModal() {
  modalAttrs(1).attrs.onClosed();
}

function thumbUp() {
  return screen.getByRole('button', { name: /utile/i });
}

function thumbDown() {
  return screen.getByRole('button', { name: /pas satisfaisant/i });
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
    renderThumbs({ vote_type: 'POSITIVE', comment: null, reasons: [] });

    expect(thumbUp()).toHaveAttribute('aria-pressed', 'true');
  });

  it('retracts an existing vote without opening the modal', async () => {
    renderThumbs({ vote_type: 'POSITIVE', comment: 'bien', reasons: [] });

    await userEvent.click(thumbUp());

    await waitFor(() => expect(remove).toHaveBeenCalledWith(42));
    expect(open).not.toHaveBeenCalled();
  });

  it('confirms a retraction with the emptied thumb alone, never a success banner', async () => {
    renderThumbs({ vote_type: 'POSITIVE', comment: 'bien', reasons: [] });

    await userEvent.click(thumbUp());

    await waitFor(() => expect(remove).toHaveBeenCalled());
    expect(addSuccessMessage).not.toHaveBeenCalled();
  });

  it('warns the user when the retraction fails', async () => {
    remove.mockRejectedValue(new Error('boom'));
    renderThumbs({ vote_type: 'POSITIVE', comment: 'bien', reasons: [] });

    await userEvent.click(thumbUp());

    await waitFor(() => expect(addErrorMessage).toHaveBeenCalled());
  });

  it('closes the modal and thanks the user once the vote is recorded', async () => {
    upsert.mockResolvedValue({ vote_type: 'POSITIVE', comment: null, reasons: [] });
    renderThumbs();
    await userEvent.click(thumbUp());

    submitPositiveModal('clair et fidèle');

    await waitFor(() => expect(addSuccessMessage).toHaveBeenCalled());
    expect(close).toHaveBeenCalled();
  });

  it('keeps the modal open and warns the user when the vote cannot be saved', async () => {
    upsert.mockRejectedValue(new Error('boom'));
    renderThumbs();
    await userEvent.click(thumbUp());

    submitPositiveModal('un long retour');

    await waitFor(() => expect(addErrorMessage).toHaveBeenCalled());
    expect(close).not.toHaveBeenCalled();
    expect(addSuccessMessage).not.toHaveBeenCalled();
  });

  it('drops a blank comment rather than sending whitespace', async () => {
    upsert.mockResolvedValue({ vote_type: 'POSITIVE', comment: null, reasons: [] });
    renderThumbs();
    await userEvent.click(thumbUp());

    submitPositiveModal('   ');

    await waitFor(() => expect(upsert).toHaveBeenCalledWith(42, { vote_type: 'POSITIVE' }));
  });

  it('opens the thumb-down modal and records nothing until it is submitted', async () => {
    renderThumbs();

    await userEvent.click(thumbDown());

    expect(open).toHaveBeenCalled();
    expect(upsert).not.toHaveBeenCalled();
    expect(remove).not.toHaveBeenCalled();
  });

  it('shows the vote as cast when a negative feedback exists', () => {
    renderThumbs({ vote_type: 'NEGATIVE', comment: null, reasons: ['OFF_TOPIC'] });

    expect(thumbDown()).toHaveAttribute('aria-pressed', 'true');
    expect(thumbUp()).toHaveAttribute('aria-pressed', 'false');
  });

  it('retracts an existing negative vote without opening the modal', async () => {
    renderThumbs({ vote_type: 'NEGATIVE', comment: null, reasons: ['OFF_TOPIC'] });

    await userEvent.click(thumbDown());

    await waitFor(() => expect(remove).toHaveBeenCalledWith(42));
    expect(open).not.toHaveBeenCalled();
  });

  it('records the reasons and the comment the user gave for a thumb down', async () => {
    upsert.mockResolvedValue({
      vote_type: 'NEGATIVE',
      comment: 'hors sujet',
      reasons: ['OFF_TOPIC'],
    });
    renderThumbs();
    await userEvent.click(thumbDown());

    submitNegativeModal({ reasons: ['OFF_TOPIC'], comment: 'hors sujet' });

    await waitFor(() =>
      expect(upsert).toHaveBeenCalledWith(42, {
        vote_type: 'NEGATIVE',
        comment: 'hors sujet',
        reasons: ['OFF_TOPIC'],
      }),
    );
    expect(addSuccessMessage).toHaveBeenCalled();
  });

  it('keeps the reasons when the thumb down carries no comment', async () => {
    upsert.mockResolvedValue({ vote_type: 'NEGATIVE', comment: null, reasons: ['OFF_TOPIC'] });
    renderThumbs();
    await userEvent.click(thumbDown());

    submitNegativeModal({ reasons: ['OFF_TOPIC'], comment: '  ' });

    await waitFor(() =>
      expect(upsert).toHaveBeenCalledWith(42, {
        vote_type: 'NEGATIVE',
        reasons: ['OFF_TOPIC'],
      }),
    );
  });

  it('switches the thumbs at once when the user changes their mind, saving nothing yet', async () => {
    renderThumbs({ vote_type: 'POSITIVE', comment: 'bien', reasons: [] });

    await userEvent.click(thumbDown());

    expect(thumbDown()).toHaveAttribute('aria-pressed', 'true');
    expect(thumbUp()).toHaveAttribute('aria-pressed', 'false');
    expect(open).toHaveBeenCalled();
    expect(upsert).not.toHaveBeenCalled();
    expect(remove).not.toHaveBeenCalled();
  });

  it('gives the previous vote back when the user closes the modal without submitting', async () => {
    renderThumbs({ vote_type: 'POSITIVE', comment: 'bien', reasons: [] });
    await userEvent.click(thumbDown());

    dismissNegativeModal();

    await waitFor(() => expect(thumbUp()).toHaveAttribute('aria-pressed', 'true'));
    expect(thumbDown()).toHaveAttribute('aria-pressed', 'false');
    expect(upsert).not.toHaveBeenCalled();
    expect(remove).not.toHaveBeenCalled();
  });

  it('replaces the previous opinion when the user submits the opposite vote', async () => {
    upsert.mockResolvedValue({ vote_type: 'NEGATIVE', comment: null, reasons: ['OFF_TOPIC'] });
    renderThumbs({ vote_type: 'POSITIVE', comment: 'bien', reasons: [] });
    await userEvent.click(thumbDown());

    submitNegativeModal({ reasons: ['OFF_TOPIC'], comment: '' });

    await waitFor(() => expect(addSuccessMessage).toHaveBeenCalled());
    expect(thumbDown()).toHaveAttribute('aria-pressed', 'true');
    expect(thumbUp()).toHaveAttribute('aria-pressed', 'false');
  });

  it('does not undo what the user is deciding when the deliverables refresh', async () => {
    const { rerender } = renderThumbs({ vote_type: 'POSITIVE', comment: 'bien', reasons: [] });
    await userEvent.click(thumbDown());

    await rerender({
      deliverable: deliverable({ vote_type: 'POSITIVE', comment: 'bien', reasons: [] }),
    });

    expect(thumbDown()).toHaveAttribute('aria-pressed', 'true');
    expect(thumbUp()).toHaveAttribute('aria-pressed', 'false');
  });

  it('keeps the recorded vote on screen once the modal has finished closing', async () => {
    upsert.mockResolvedValue({ vote_type: 'NEGATIVE', comment: null, reasons: ['OFF_TOPIC'] });
    const { rerender } = renderThumbs({ vote_type: 'POSITIVE', comment: 'bien', reasons: [] });
    await userEvent.click(thumbDown());
    submitNegativeModal({ reasons: ['OFF_TOPIC'], comment: '' });
    await waitFor(() => expect(addSuccessMessage).toHaveBeenCalled());
    await rerender({
      deliverable: deliverable({ vote_type: 'NEGATIVE', comment: null, reasons: ['OFF_TOPIC'] }),
    });

    dismissNegativeModal();
    await nextTick();

    expect(thumbDown()).toHaveAttribute('aria-pressed', 'true');
    expect(thumbUp()).toHaveAttribute('aria-pressed', 'false');
  });

  it('keeps the thumb down empty when the negative vote cannot be saved', async () => {
    upsert.mockRejectedValue(new Error('boom'));
    renderThumbs();
    await userEvent.click(thumbDown());

    submitNegativeModal({ reasons: ['OFF_TOPIC'], comment: '' });

    await waitFor(() => expect(addErrorMessage).toHaveBeenCalled());
    expect(close).not.toHaveBeenCalled();
    expect(thumbDown()).toHaveAttribute('aria-pressed', 'false');
  });
});
