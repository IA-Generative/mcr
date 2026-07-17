import { describe, it, expect, vi } from 'vitest';
import { transcriptionTag, reportTag } from './deliverables.service';
import type { DeliverableStatus, DeliverableType } from './deliverables.types';

vi.mock('@/plugins/i18n', () => ({ t: vi.fn((key: string) => key) }));

function del(type: DeliverableType, status: DeliverableStatus) {
  return { type, status };
}

describe('transcriptionTag', () => {
  it('returns the TRANSCRIPTION deliverable status', () => {
    expect(transcriptionTag([del('TRANSCRIPTION', 'IN_PROGRESS')])).toBe('IN_PROGRESS');
    expect(transcriptionTag([del('TRANSCRIPTION', 'AVAILABLE')])).toBe('AVAILABLE');
  });

  it('defaults to PENDING when no TRANSCRIPTION deliverable exists', () => {
    expect(transcriptionTag([])).toBe('PENDING');
    expect(transcriptionTag([del('DECISION_RECORD', 'AVAILABLE')])).toBe('PENDING');
  });
});

describe('reportTag', () => {
  it('defaults to PENDING when no report deliverable exists', () => {
    expect(reportTag([])).toBe('PENDING');
    expect(reportTag([del('TRANSCRIPTION', 'AVAILABLE')])).toBe('PENDING');
  });

  it('prioritises AVAILABLE over the rest', () => {
    expect(
      reportTag([del('DECISION_RECORD', 'FAILED'), del('DETAILED_SYNTHESIS', 'AVAILABLE')]),
    ).toBe('AVAILABLE');
  });

  it('prioritises FAILED over IN_PROGRESS', () => {
    expect(
      reportTag([del('DECISION_RECORD', 'FAILED'), del('DETAILED_SYNTHESIS', 'IN_PROGRESS')]),
    ).toBe('FAILED');
  });

  it('prioritises IN_PROGRESS over PENDING', () => {
    expect(
      reportTag([del('DECISION_RECORD', 'IN_PROGRESS'), del('DETAILED_SYNTHESIS', 'PENDING')]),
    ).toBe('IN_PROGRESS');
  });

  it('falls back to PENDING', () => {
    expect(reportTag([del('CUSTOM_REPORT', 'PENDING')])).toBe('PENDING');
  });
});
