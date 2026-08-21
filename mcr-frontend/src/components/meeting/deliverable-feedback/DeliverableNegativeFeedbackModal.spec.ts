import { screen, waitFor } from '@testing-library/vue';
import userEvent from '@testing-library/user-event';
import { renderWithPlugins } from '@/vitest.setup';
import type { ReasonCatalogue } from '@/services/deliverable-feedback/deliverable-feedback.types';

const { fetchReasons } = vi.hoisted(() => ({ fetchReasons: vi.fn() }));

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

vi.mock('@/services/deliverable-feedback/deliverable-feedback.service', () => ({
  getDeliverableFeedbackReasons: () => fetchReasons(),
}));

import DeliverableNegativeFeedbackModal from './DeliverableNegativeFeedbackModal.vue';

const CATALOGUE: ReasonCatalogue = {
  TRANSCRIPTION: {
    deliverable_group: 'TRANSCRIPTION',
    reasons: ['WORD_ERRORS', 'MISIDENTIFIED_SPEAKERS', 'OTHER'],
  },
  DECISION_RECORD: {
    deliverable_group: 'STRUCTURED',
    reasons: ['MISSING_INFORMATION', 'OFF_TOPIC', 'OTHER'],
  },
};

function renderModal(props: Record<string, unknown> = {}) {
  const onSubmit = vi.fn();
  const onUpdateDraft = vi.fn();
  const { rerender } = renderWithPlugins(DeliverableNegativeFeedbackModal, {
    props: {
      deliverableType: 'DECISION_RECORD',
      isSubmitting: false,
      onSubmit,
      onUpdateDraft,
      ...props,
    },
  });
  return { rerender, onSubmit, onUpdateDraft };
}

const chip = (name: string | RegExp) => screen.getByRole('button', { name });
const commentBox = () => screen.getByRole('textbox');
const submitButton = () => screen.getByRole('button', { name: /^envoyer$/i });

async function renderWithCatalogue(props: Record<string, unknown> = {}) {
  const utils = renderModal(props);
  await screen.findByRole('button', { name: 'Hors sujet' });
  return utils;
}

describe('DeliverableNegativeFeedbackModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchReasons.mockResolvedValue(CATALOGUE);
  });

  it('offers the reasons of the rated deliverable, and no other', async () => {
    await renderWithCatalogue();

    expect(chip('Informations manquantes')).toBeInTheDocument();
    expect(chip('Hors sujet')).toBeInTheDocument();
    expect(chip('Autre')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Erreurs de mots' })).not.toBeInTheDocument();
  });

  it('offers the transcription reasons when the transcription is what was rated', async () => {
    renderModal({ deliverableType: 'TRANSCRIPTION' });

    await waitFor(() => expect(chip('Erreurs de mots')).toBeInTheDocument());
    expect(screen.queryByRole('button', { name: 'Hors sujet' })).not.toBeInTheDocument();
  });

  it('opens blank, with nothing preselected', async () => {
    await renderWithCatalogue();

    expect(chip('Hors sujet')).toHaveAttribute('aria-pressed', 'false');
    expect(commentBox()).toHaveValue('');
  });

  it('opens on the reasons and the comment already given for this deliverable', async () => {
    await renderWithCatalogue({
      initialReasons: ['OFF_TOPIC'],
      initialComment: 'globalement à côté',
    });

    expect(chip('Hors sujet')).toHaveAttribute('aria-pressed', 'true');
    expect(chip('Informations manquantes')).toHaveAttribute('aria-pressed', 'false');
    expect(commentBox()).toHaveValue('globalement à côté');
  });

  it('submits what it opened on when the user changes nothing', async () => {
    const { onSubmit } = await renderWithCatalogue({
      initialReasons: ['OFF_TOPIC'],
      initialComment: 'globalement à côté',
    });

    await userEvent.click(submitButton());

    expect(onSubmit).toHaveBeenCalledWith({
      reasons: ['OFF_TOPIC'],
      comment: 'globalement à côté',
    });
  });

  it('reports the reasons and the text as they change, so they outlive the modal being destroyed', async () => {
    const { onUpdateDraft } = await renderWithCatalogue();

    await userEvent.click(chip('Hors sujet'));
    await userEvent.type(commentBox(), 'à côté');

    expect(onUpdateDraft).toHaveBeenLastCalledWith({
      reasons: ['OFF_TOPIC'],
      comment: 'à côté',
    });
  });

  it('reports nothing when it is merely opened and closed untouched', async () => {
    const { onUpdateDraft } = await renderWithCatalogue({
      initialReasons: ['OFF_TOPIC'],
      initialComment: 'globalement à côté',
    });

    expect(onUpdateDraft).not.toHaveBeenCalled();
  });

  it('lets the user drop a reason it opened on', async () => {
    const { onSubmit } = await renderWithCatalogue({
      initialReasons: ['OFF_TOPIC', 'MISSING_INFORMATION'],
    });

    await userEvent.click(chip('Hors sujet'));
    await userEvent.click(submitButton());

    expect(onSubmit).toHaveBeenCalledWith({ reasons: ['MISSING_INFORMATION'], comment: '' });
  });

  it('lets the user report several reasons at once', async () => {
    const { onSubmit } = await renderWithCatalogue();

    await userEvent.click(chip('Hors sujet'));
    await userEvent.click(chip('Informations manquantes'));
    await userEvent.click(submitButton());

    expect(onSubmit).toHaveBeenCalledWith({
      reasons: ['OFF_TOPIC', 'MISSING_INFORMATION'],
      comment: '',
    });
  });

  it('lets the user take back a reason ticked by mistake', async () => {
    const { onSubmit } = await renderWithCatalogue();

    await userEvent.click(chip('Hors sujet'));
    await userEvent.click(chip('Informations manquantes'));
    await userEvent.click(chip('Hors sujet'));
    await userEvent.click(submitButton());

    expect(onSubmit).toHaveBeenCalledWith({ reasons: ['MISSING_INFORMATION'], comment: '' });
  });

  it('refuses to send a thumb down that says nothing', async () => {
    const { onSubmit } = await renderWithCatalogue();

    await userEvent.click(submitButton());

    expect(onSubmit).not.toHaveBeenCalled();
    expect(
      screen.getByText('Vous devez sélectionner un motif ou laisser un commentaire'),
    ).toBeInTheDocument();
  });

  it('asks the user to spell out "Autre" when it is the only reason given', async () => {
    const { onSubmit } = await renderWithCatalogue();

    await userEvent.click(chip('Autre'));
    await userEvent.click(submitButton());

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByText("Précisez ce qui n'allait pas")).toBeInTheDocument();
  });

  it('sends "Autre" once it is spelled out', async () => {
    const { onSubmit } = await renderWithCatalogue();

    await userEvent.click(chip('Autre'));
    await userEvent.type(commentBox(), 'les tableaux ont perdu leur en-tête');

    await userEvent.click(submitButton());

    expect(onSubmit).toHaveBeenCalledWith({
      reasons: ['OTHER'],
      comment: 'les tableaux ont perdu leur en-tête',
    });
  });

  it('sends a comment given without any reason', async () => {
    const { onSubmit } = await renderWithCatalogue();

    await userEvent.type(commentBox(), 'globalement à côté');
    await userEvent.click(submitButton());

    expect(onSubmit).toHaveBeenCalledWith({ reasons: [], comment: 'globalement à côté' });
  });

  it('clears the complaint once the user fixes it', async () => {
    await renderWithCatalogue();
    await userEvent.click(submitButton());

    await userEvent.click(chip('Hors sujet'));

    expect(
      screen.queryByText('Vous devez sélectionner un motif ou laisser un commentaire'),
    ).not.toBeInTheDocument();
  });

  it('blocks the modal rather than accept an unmotivated thumb down when reasons are missing', async () => {
    fetchReasons.mockRejectedValue(new Error('boom'));
    const { onSubmit } = renderModal();

    await screen.findByText(/motifs n.ont pas pu être chargés/);
    expect(screen.queryByRole('button', { name: 'Autre' })).not.toBeInTheDocument();
    expect(submitButton()).toBeDisabled();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('lets the user try again after the reasons failed to load', async () => {
    fetchReasons.mockRejectedValueOnce(new Error('boom')).mockResolvedValue(CATALOGUE);
    renderModal();
    await screen.findByRole('button', { name: /réessayer/i });

    await userEvent.click(screen.getByRole('button', { name: /réessayer/i }));

    await waitFor(() => expect(chip('Hors sujet')).toBeInTheDocument());
    expect(submitButton()).toBeEnabled();
  });

  it('blocks the modal for a deliverable the catalogue says nothing about', async () => {
    renderModal({ deliverableType: 'CUSTOM_REPORT' });

    await screen.findByText(/motifs n.ont pas pu être chargés/);
    expect(submitButton()).toBeDisabled();
    expect(screen.queryByRole('button', { name: 'Autre' })).not.toBeInTheDocument();
  });

  it('does not send the same feedback twice while a submission is in flight', async () => {
    const { onSubmit } = await renderWithCatalogue({ isSubmitting: true });

    await userEvent.click(chip('Hors sujet'));
    await userEvent.click(submitButton());

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('keeps what the user wrote while the submission is in flight', async () => {
    const { rerender } = await renderWithCatalogue();
    await userEvent.click(chip('Hors sujet'));
    await userEvent.type(commentBox(), 'un long retour');

    await rerender({ isSubmitting: true });

    expect(commentBox()).toHaveValue('un long retour');
    expect(chip('Hors sujet')).toHaveAttribute('aria-pressed', 'true');
  });

  it('downloads the catalogue once, however many reasons the user ticks', async () => {
    await renderWithCatalogue();

    await userEvent.click(chip('Hors sujet'));
    await userEvent.click(chip('Autre'));

    expect(fetchReasons).toHaveBeenCalledTimes(1);
  });
});
