import { createPinia, setActivePinia } from 'pinia';
import type { DeliverableDto } from '@/services/deliverables/deliverables.types';
import { useDeliverableFeedbackDraft } from './use-deliverable-feedback-draft';

function deliverable(id: number, feedback: DeliverableDto['feedback'] = null): DeliverableDto {
  return {
    id,
    meeting_id: 1,
    type: 'DECISION_RECORD',
    status: 'AVAILABLE',
    external_url: null,
    created_at: '2026-07-10T00:00:00Z',
    updated_at: '2026-07-10T00:00:00Z',
    feedback,
  };
}

describe('useDeliverableFeedbackDraft', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('offers the opinion held in base to a modal of the same vote sense', () => {
    const drafts = useDeliverableFeedbackDraft();

    drafts.seed([
      deliverable(42, { vote_type: 'NEGATIVE', comment: 'hors sujet', reasons: ['OFF_TOPIC'] }),
    ]);

    expect(drafts.draftFor(42, 'NEGATIVE')).toEqual({
      vote_type: 'NEGATIVE',
      comment: 'hors sujet',
      reasons: ['OFF_TOPIC'],
    });
  });

  it('leaves a modal of the opposite vote sense blank', () => {
    const drafts = useDeliverableFeedbackDraft();

    drafts.seed([deliverable(42, { vote_type: 'POSITIVE', comment: 'bien', reasons: [] })]);

    expect(drafts.draftFor(42, 'NEGATIVE')).toBeUndefined();
    expect(drafts.draftFor(42, 'POSITIVE')?.comment).toBe('bien');
  });

  it('keeps each opinion to the deliverable it was given on', () => {
    const drafts = useDeliverableFeedbackDraft();

    drafts.seed([
      deliverable(42, { vote_type: 'POSITIVE', comment: 'bien', reasons: [] }),
      deliverable(43),
    ]);

    expect(drafts.draftFor(43, 'POSITIVE')).toBeUndefined();
    expect(drafts.draftFor(42, 'POSITIVE')?.comment).toBe('bien');
  });

  it('keeps the opinion when a later load no longer carries the feedback, so a retracted vote stays recoverable', () => {
    const drafts = useDeliverableFeedbackDraft();
    drafts.seed([deliverable(42, { vote_type: 'POSITIVE', comment: 'bien', reasons: [] })]);

    drafts.seed([deliverable(42)]);

    expect(drafts.draftFor(42, 'POSITIVE')?.comment).toBe('bien');
  });

  it('offers an empty comment field, never a null one, when the opinion carried no comment', () => {
    const drafts = useDeliverableFeedbackDraft();

    drafts.seed([deliverable(42, { vote_type: 'POSITIVE', comment: null, reasons: [] })]);

    expect(drafts.draftFor(42, 'POSITIVE')?.comment).toBe('');
  });
});
