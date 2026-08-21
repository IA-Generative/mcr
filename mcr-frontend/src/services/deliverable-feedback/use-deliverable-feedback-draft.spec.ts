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

  it('offers back what the user typed without submitting it', () => {
    const drafts = useDeliverableFeedbackDraft();

    drafts.remember(42, { vote_type: 'NEGATIVE', comment: 'à revoir', reasons: ['OFF_TOPIC'] });

    expect(drafts.draftFor(42, 'NEGATIVE')).toEqual({
      vote_type: 'NEGATIVE',
      comment: 'à revoir',
      reasons: ['OFF_TOPIC'],
    });
  });

  it('holds a single intention per deliverable, so a new vote sense replaces the previous', () => {
    const drafts = useDeliverableFeedbackDraft();
    drafts.remember(42, { vote_type: 'POSITIVE', comment: 'bien', reasons: [] });

    drafts.remember(42, { vote_type: 'NEGATIVE', comment: 'à revoir', reasons: [] });

    expect(drafts.draftFor(42, 'POSITIVE')).toBeUndefined();
    expect(drafts.draftFor(42, 'NEGATIVE')?.comment).toBe('à revoir');
  });

  it('does not let a deliverables load overwrite what the user typed without submitting', () => {
    const drafts = useDeliverableFeedbackDraft();
    drafts.seed([deliverable(42, { vote_type: 'POSITIVE', comment: 'bien', reasons: [] })]);
    drafts.remember(42, { vote_type: 'POSITIVE', comment: 'bien, mais à nuancer', reasons: [] });

    drafts.seed([deliverable(42, { vote_type: 'POSITIVE', comment: 'bien', reasons: [] })]);

    expect(drafts.draftFor(42, 'POSITIVE')?.comment).toBe('bien, mais à nuancer');
  });

  it('forgets the targeted deliverable alone', () => {
    const drafts = useDeliverableFeedbackDraft();
    drafts.remember(42, { vote_type: 'POSITIVE', comment: 'bien', reasons: [] });
    drafts.remember(43, { vote_type: 'NEGATIVE', comment: 'à revoir', reasons: ['OFF_TOPIC'] });

    drafts.forget(42);

    expect(drafts.draftFor(42, 'POSITIVE')).toBeUndefined();
    expect(drafts.draftFor(43, 'NEGATIVE')?.comment).toBe('à revoir');
  });
});
