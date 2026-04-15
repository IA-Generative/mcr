import { describe, it, expect, vi } from 'vitest';
import { getTranscriptionStatus, MeetingStatus } from '@/services/meetings/meetings.types';

vi.mock('@/plugins/i18n', () => ({ t: vi.fn((key: string) => key) }));

describe('getTranscriptionStatus', () => {
  it.each([
    'NONE',
    'CAPTURE_PENDING',
    'IMPORT_PENDING',
    'CAPTURE_BOT_IS_CONNECTING',
    'CAPTURE_BOT_CONNECTION_FAILED',
    'CAPTURE_IN_PROGRESS',
    'CAPTURE_DONE',
    'TRANSCRIPTION_PENDING',
  ] satisfies MeetingStatus[])('should_return_pending_for_%s', (status) => {
    expect(getTranscriptionStatus(status)).toBe('PENDING');
  });

  it('should_return_info_for_TRANSCRIPTION_IN_PROGRESS', () => {
    expect(getTranscriptionStatus('TRANSCRIPTION_IN_PROGRESS')).toBe('IN_PROGRESS');
  });

  it.each(['TRANSCRIPTION_DONE', 'REPORT_PENDING', 'REPORT_DONE'] satisfies MeetingStatus[])(
    'should_return_success_for_%s',
    (status) => {
      expect(getTranscriptionStatus(status)).toBe('DONE');
    },
  );

  it.each(['CAPTURE_FAILED', 'TRANSCRIPTION_FAILED'] satisfies MeetingStatus[])(
    'should_return_error_for_%s',
    (status) => {
      expect(getTranscriptionStatus(status)).toBe('FAILED');
    },
  );

  it.each(MeetingStatus)('should_handle_%s_without_falling_back_to_default', (status) => {
    expect(getTranscriptionStatus(status)).toBeDefined();
  });
});
