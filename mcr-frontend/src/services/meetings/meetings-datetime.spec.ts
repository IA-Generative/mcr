import { describe, it, expect, vi, beforeAll, afterAll } from 'vitest';
import {
  getCalendarDateFromIso8601,
  getTimeFromIso8601,
  getMeetingDuration,
} from './meetings-datetime';
import type { MeetingDetailDto } from './meetings.types';

vi.mock('@sentry/vue', () => ({
  logger: { error: vi.fn() },
}));

const originalTZ = process.env.TZ;
beforeAll(() => {
  process.env.TZ = 'Europe/Paris';
});
afterAll(() => {
  process.env.TZ = originalTZ;
});

describe('getCalendarDateFromIso8601', () => {
  it('should format a standard date as DD/MM/YY', () => {
    // UTC 10:30 → Paris 11:30 (CET +1), same day
    expect(getCalendarDateFromIso8601('2025-03-15T10:30:00Z')).toBe('15/03/25');
  });

  it('should pad single-digit day and month with zeros', () => {
    expect(getCalendarDateFromIso8601('2025-01-05T12:00:00Z')).toBe('05/01/25');
  });

  it('should handle end of year correctly', () => {
    expect(getCalendarDateFromIso8601('2024-12-31T12:00:00Z')).toBe('31/12/24');
  });
});

describe('getTimeFromIso8601', () => {
  it('should format a standard time as HHhMM', () => {
    // UTC 14:30 → Paris 15:30 (CET +1, March before DST switch)
    expect(getTimeFromIso8601('2025-03-15T14:30:00Z')).toBe('15h30');
  });

  it('should format early morning with padding', () => {
    // UTC 00:00 → Paris 01:00 (CET +1, January)
    expect(getTimeFromIso8601('2025-01-01T00:00:00Z')).toBe('01h00');
  });

  it('should pad single-digit hours and minutes', () => {
    // UTC 09:05 → Paris 11:05 (CEST +2, June)
    expect(getTimeFromIso8601('2025-06-10T09:05:00Z')).toBe('11h05');
  });
});

describe('getMeetingDuration', () => {
  function makeMeeting(startDate?: string, endDate?: string): MeetingDetailDto {
    return {
      id: 1,
      name: 'Test',
      name_platform: 'VISIO',
      status: 'NONE',
      creation_date: '2025-01-01T00:00:00Z',
      start_date: startDate,
      end_date: endDate,
      url: null,
      meeting_password: null,
      meeting_platform_id: null,
      deliverables: [],
    } as MeetingDetailDto;
  }

  it('should compute a 1h30 duration', () => {
    const meeting = makeMeeting('2025-01-01T10:00:00Z', '2025-01-01T11:30:00Z');
    expect(getMeetingDuration(meeting)).toBe('01:30:00');
  });

  it('should compute a duration shorter than 1 minute', () => {
    const meeting = makeMeeting('2025-01-01T10:00:00Z', '2025-01-01T10:00:45Z');
    expect(getMeetingDuration(meeting)).toBe('00:00:45');
  });

  it('should compute a duration with hours, minutes and seconds', () => {
    const meeting = makeMeeting('2025-01-01T08:00:00Z', '2025-01-01T10:15:30Z');
    expect(getMeetingDuration(meeting)).toBe('02:15:30');
  });

  it('should return empty string when start_date is undefined', () => {
    const meeting = makeMeeting(undefined, '2025-01-01T11:00:00Z');
    expect(getMeetingDuration(meeting)).toBe('');
  });

  it('should return empty string when end_date is undefined', () => {
    const meeting = makeMeeting('2025-01-01T10:00:00Z', undefined);
    expect(getMeetingDuration(meeting)).toBe('');
  });
});
