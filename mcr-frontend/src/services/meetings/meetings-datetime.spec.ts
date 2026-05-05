import { describe, it, expect, vi, beforeAll, afterAll } from 'vitest';
import {
  getCalendarDateFromIso8601,
  getNumberOfDaysBeforeMeetingDeletion,
  getTimeFromIso8601,
  calculateDuration,
  leftPad,
  meetingDateIsInAlertPeriod,
} from './meetings-datetime';
import { subDays, formatISO } from 'date-fns';

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

function creationDateDaysAgo(days: number): string {
  return formatISO(subDays(new Date(), days));
}

describe('meetingDateIsInAlertPeriod', () => {
  it('returns false for a meeting created 10 days ago', () => {
    expect(meetingDateIsInAlertPeriod(creationDateDaysAgo(10))).toBe(false);
  });

  it('returns false for a meeting created exactly 20 days ago', () => {
    expect(meetingDateIsInAlertPeriod(creationDateDaysAgo(20))).toBe(false);
  });

  it('returns true for a meeting created 25 days ago', () => {
    expect(meetingDateIsInAlertPeriod(creationDateDaysAgo(25))).toBe(true);
  });
});

describe('getNumberOfDaysBeforeMeetingDeletion', () => {
  it('returns 20 for a meeting created 10 days ago', () => {
    expect(getNumberOfDaysBeforeMeetingDeletion(creationDateDaysAgo(10))).toBe(20);
  });

  it('returns 5 for a meeting created 25 days ago', () => {
    expect(getNumberOfDaysBeforeMeetingDeletion(creationDateDaysAgo(25))).toBe(5);
  });

  it('returns 0 for a meeting created more than 30 days ago', () => {
    expect(getNumberOfDaysBeforeMeetingDeletion(creationDateDaysAgo(35))).toBe(0);
  });
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

describe('leftPad', () => {
  it('should pad single digit with leading zero', () => {
    expect(leftPad(5)).toBe('05');
  });

  it('should leave two-digit number unchanged', () => {
    expect(leftPad(42)).toBe('42');
  });

  it('should pad zero', () => {
    expect(leftPad(0)).toBe('00');
  });
});

describe('getMeetingDuration', () => {
  it('should compute a 1h30 duration', () => {
    expect(calculateDuration('2025-01-01T10:00:00Z', '2025-01-01T11:30:00Z')).toBe('01:30:00');
  });

  it('should compute a duration shorter than 1 minute', () => {
    expect(calculateDuration('2025-01-01T10:00:00Z', '2025-01-01T10:00:45Z')).toBe('00:00:45');
  });

  it('should compute a duration with hours, minutes and seconds', () => {
    expect(calculateDuration('2025-01-01T08:00:00Z', '2025-01-01T10:15:30Z')).toBe('02:15:30');
  });

  it('should return empty string when start_date is undefined', () => {
    expect(calculateDuration(undefined, '2025-01-01T11:00:00Z')).toBe('');
  });

  it('should return empty string when end_date is undefined', () => {
    expect(calculateDuration('2025-01-01T10:00:00Z', undefined)).toBe('');
  });
});
