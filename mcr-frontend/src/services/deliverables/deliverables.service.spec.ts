import { describe, it, expect, vi } from 'vitest';
import { getTranscriptionStatus, getReportStatus } from './deliverables.service';
import type { DeliverableStatus, DeliverableType } from './deliverables.types';

vi.mock('@/plugins/i18n', () => ({ t: vi.fn((key: string) => key) }));

function fakeDeliverable(type: DeliverableType, status: DeliverableStatus) {
  return { type, status };
}

describe('getTranscriptionStatus', () => {
  it('returns the TRANSCRIPTION deliverable status', () => {
    expect(getTranscriptionStatus([fakeDeliverable('TRANSCRIPTION', 'IN_PROGRESS')])).toBe(
      'IN_PROGRESS',
    );
    expect(getTranscriptionStatus([fakeDeliverable('TRANSCRIPTION', 'AVAILABLE')])).toBe(
      'AVAILABLE',
    );
  });

  it('defaults to PENDING when no TRANSCRIPTION deliverable exists', () => {
    expect(getTranscriptionStatus([])).toBe('PENDING');
    expect(getTranscriptionStatus([fakeDeliverable('DECISION_RECORD', 'AVAILABLE')])).toBe(
      'PENDING',
    );
  });
});

describe('getReportStatus', () => {
  it('defaults to PENDING when no report deliverable exists', () => {
    expect(getReportStatus([])).toBe('PENDING');
    expect(getReportStatus([fakeDeliverable('TRANSCRIPTION', 'AVAILABLE')])).toBe('PENDING');
  });

  it('prioritises AVAILABLE over the rest', () => {
    expect(
      getReportStatus([
        fakeDeliverable('DECISION_RECORD', 'FAILED'),
        fakeDeliverable('DETAILED_SYNTHESIS', 'AVAILABLE'),
      ]),
    ).toBe('AVAILABLE');
  });

  it('prioritises FAILED over IN_PROGRESS', () => {
    expect(
      getReportStatus([
        fakeDeliverable('DECISION_RECORD', 'FAILED'),
        fakeDeliverable('DETAILED_SYNTHESIS', 'IN_PROGRESS'),
      ]),
    ).toBe('FAILED');
  });

  it('prioritises IN_PROGRESS over PENDING', () => {
    expect(
      getReportStatus([
        fakeDeliverable('DECISION_RECORD', 'IN_PROGRESS'),
        fakeDeliverable('DETAILED_SYNTHESIS', 'PENDING'),
      ]),
    ).toBe('IN_PROGRESS');
  });

  it('falls back to PENDING', () => {
    expect(getReportStatus([fakeDeliverable('CUSTOM_REPORT', 'PENDING')])).toBe('PENDING');
  });
});
