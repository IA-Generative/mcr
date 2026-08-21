import { describe, it, expect, vi } from 'vitest';
import { getTranscriptionStatus, getReportStatus } from './deliverables.service';
import { DeliverableStatus, type DeliverableType } from './deliverables.types';

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
  it.each(DeliverableStatus)('mirrors the STRUCTURED_MINUTES status %s', (status) => {
    expect(getReportStatus([fakeDeliverable('STRUCTURED_MINUTES', status)])).toBe(status);
  });

  it('defaults to PENDING when no STRUCTURED_MINUTES deliverable exists', () => {
    expect(getReportStatus([])).toBe('PENDING');
    expect(getReportStatus([fakeDeliverable('TRANSCRIPTION', 'AVAILABLE')])).toBe('PENDING');
  });

  it('stays PENDING when only the other reports are available', () => {
    expect(
      getReportStatus([
        fakeDeliverable('DECISION_RECORD', 'AVAILABLE'),
        fakeDeliverable('DETAILED_SYNTHESIS', 'AVAILABLE'),
        fakeDeliverable('CUSTOM_REPORT', 'AVAILABLE'),
      ]),
    ).toBe('PENDING');
  });

  it('ignores the other reports when the STRUCTURED_MINUTES deliverable exists', () => {
    expect(
      getReportStatus([
        fakeDeliverable('DECISION_RECORD', 'AVAILABLE'),
        fakeDeliverable('CUSTOM_REPORT', 'FAILED'),
        fakeDeliverable('STRUCTURED_MINUTES', 'IN_PROGRESS'),
      ]),
    ).toBe('IN_PROGRESS');
  });
});
