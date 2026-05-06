import { describe, it, expect, vi } from 'vitest';
import { MeetingStatus } from '@/services/meetings/meetings.types';
import { getTranscriptionStatus, getReportStatus } from './deliverables.service';

vi.mock('@/plugins/i18n', () => ({ t: vi.fn((key: string) => key) }));

describe('getTranscriptionStatus', () => {
  it.each([
    'NONE',
    'CAPTURE_PENDING',
    'IMPORT_PENDING',
    'CAPTURE_BOT_IS_CONNECTING',
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
      expect(getTranscriptionStatus(status)).toBe('AVAILABLE');
    },
  );

  it.each([
    'CAPTURE_FAILED',
    'TRANSCRIPTION_FAILED',
    'CAPTURE_BOT_CONNECTION_FAILED',
  ] satisfies MeetingStatus[])('should_return_error_for_%s', (status) => {
    expect(getTranscriptionStatus(status)).toBe('FAILED');
  });

  it.each(MeetingStatus)('should_handle_%s_without_falling_back_to_default', (status) => {
    expect(getTranscriptionStatus(status)).not.toBeNull();
  });

  it('should_return_null_for_a_MeetingStatus_that_is_not_expected', () => {
    const test = 'TEST' as MeetingStatus;
    expect(getTranscriptionStatus(test)).toBeNull();
  });
});

describe('getReportStatus', () => {
  it.each([
    'NONE',
    'CAPTURE_PENDING',
    'IMPORT_PENDING',
    'CAPTURE_BOT_IS_CONNECTING',
    'CAPTURE_IN_PROGRESS',
    'CAPTURE_DONE',
    'TRANSCRIPTION_PENDING',
    'TRANSCRIPTION_IN_PROGRESS',
    'TRANSCRIPTION_DONE',
  ] satisfies MeetingStatus[])('should_return_pending_for_%s', (status) => {
    expect(getReportStatus(status)).toBe('PENDING');
  });

  it('should_return_info_for_REPORT_PENDING', () => {
    expect(getReportStatus('REPORT_PENDING')).toBe('IN_PROGRESS');
  });

  it('should_return_success_for_REPORT_DONE', () => {
    expect(getReportStatus('REPORT_DONE')).toBe('AVAILABLE');
  });

  it.each([
    'CAPTURE_FAILED',
    'TRANSCRIPTION_FAILED',
    'CAPTURE_BOT_CONNECTION_FAILED',
  ] satisfies MeetingStatus[])('should_return_error_for_%s', (status) => {
    expect(getReportStatus(status)).toBe('FAILED');
  });

  it.each(MeetingStatus)('should_handle_%s_without_falling_back_to_default', (status) => {
    expect(getReportStatus(status)).not.toBeNull();
  });

  it('should_return_null_for_a_MeetingStatus_that_is_not_expected', () => {
    const test = 'TEST' as MeetingStatus;
    expect(getReportStatus(test)).toBeNull();
  });
});
