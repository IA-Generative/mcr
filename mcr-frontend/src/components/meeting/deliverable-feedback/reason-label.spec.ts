import { reasonLabel } from './reason-label';

describe('reasonLabel', () => {
  it('names a reason with the wording of its own group', () => {
    expect(reasonLabel('TRANSCRIPTION', 'MISIDENTIFIED_SPEAKERS')).toBe('Locuteurs mal identifiés');
  });

  it('names the same value differently in two groups when the wording differs', () => {
    expect(reasonLabel('STRUCTURED', 'MISSING_INFORMATION')).toBe('Informations manquantes');
    expect(reasonLabel('CUSTOM', 'MISSING_INFORMATION')).toBe('Informations manquantes');
  });

  it('falls back to the shared wording for a reason every group offers', () => {
    expect(reasonLabel('TRANSCRIPTION', 'OTHER')).toBe('Autre');
    expect(reasonLabel('STRUCTURED', 'OTHER')).toBe('Autre');
    expect(reasonLabel('CUSTOM', 'OTHER')).toBe('Autre');
  });

  it('shows a reason the back added before the front was translated, rather than nothing', () => {
    expect(reasonLabel('STRUCTURED', 'FRESHLY_SHIPPED_REASON')).toBe('FRESHLY_SHIPPED_REASON');
  });
});
