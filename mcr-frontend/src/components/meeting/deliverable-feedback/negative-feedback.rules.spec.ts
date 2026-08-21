import { negativeFeedbackViolation } from './negative-feedback.rules';

describe('negativeFeedbackViolation', () => {
  it('refuses a thumb down that carries neither reason nor comment', () => {
    expect(negativeFeedbackViolation({ reasons: [], comment: '' })).toBe('no-signal');
  });

  it('treats a whitespace-only comment as no comment at all', () => {
    expect(negativeFeedbackViolation({ reasons: [], comment: '   \n\t' })).toBe('no-signal');
  });

  it('accepts a reason on its own', () => {
    expect(negativeFeedbackViolation({ reasons: ['OFF_TOPIC'], comment: '' })).toBeNull();
  });

  it('accepts a comment on its own', () => {
    expect(negativeFeedbackViolation({ reasons: [], comment: 'hors sujet' })).toBeNull();
  });

  it('refuses "Autre" on its own, which carries no signal', () => {
    expect(negativeFeedbackViolation({ reasons: ['OTHER'], comment: '' })).toBe(
      'other-needs-comment',
    );
  });

  it('accepts "Autre" once it is spelled out', () => {
    expect(
      negativeFeedbackViolation({ reasons: ['OTHER'], comment: 'les tableaux ont perdu…' }),
    ).toBeNull();
  });

  it('accepts "Autre" beside another reason, which already carries signal', () => {
    expect(negativeFeedbackViolation({ reasons: ['OFF_TOPIC', 'OTHER'], comment: '' })).toBeNull();
  });
});
