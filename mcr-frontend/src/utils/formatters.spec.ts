import { describe, it, expect } from 'vitest';
import { buildDeliverableFilename } from './formatters';

describe('buildDeliverableFilename', () => {
  it('builds a basic filename', () => {
    expect(buildDeliverableFilename('Releve_Decision', 'Ma réunion')).toBe(
      'Releve_Decision_Ma_réunion.docx',
    );
  });

  it('replaces spaces with underscores', () => {
    expect(buildDeliverableFilename('Transcription', 'a b c')).toBe('Transcription_a_b_c.docx');
  });

  it('sanitises forbidden characters', () => {
    expect(buildDeliverableFilename('Transcription', 'a/b*c')).toBe('Transcription_a_b_c.docx');
  });

  it('truncates titles longer than 30 characters', () => {
    const longTitle = 'a'.repeat(50);
    expect(buildDeliverableFilename('Transcription', longTitle)).toBe(
      `Transcription_${'a'.repeat(30)}.docx`,
    );
  });

  it('falls back to Sans_Titre when title is empty', () => {
    expect(buildDeliverableFilename('Transcription', '')).toBe('Transcription_Sans_Titre.docx');
  });

  it('replaces forbidden-only titles with underscores (no empty fallback)', () => {
    expect(buildDeliverableFilename('Transcription', '///')).toBe('Transcription____.docx');
  });
});
