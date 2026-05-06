import { describe, it, expect, vi, afterEach } from 'vitest';
import { useMeetingPeremption } from './use-meeting-peremption';
import { subDays, formatISO } from 'date-fns';

function creationDateDaysAgo(days: number): string {
  return formatISO(subDays(new Date(), days));
}

describe('useMeetingPeremption', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('daysBeforeDeletion', () => {
    it('returns undefined when creationDate is undefined', () => {
      const { daysBeforeDeletion } = useMeetingPeremption(() => undefined);
      expect(daysBeforeDeletion.value).toBeUndefined();
    });

    it('returns the correct number of days for a recent meeting', () => {
      const { daysBeforeDeletion } = useMeetingPeremption(() => creationDateDaysAgo(10));
      expect(daysBeforeDeletion.value).toBe(20);
    });

    it('returns undefined for an expired meeting (> 30 days)', () => {
      const { daysBeforeDeletion } = useMeetingPeremption(() => creationDateDaysAgo(35));
      expect(daysBeforeDeletion.value).toBeUndefined();
    });

    it('returns undefined for a meeting exactly 30 days old', () => {
      const { daysBeforeDeletion } = useMeetingPeremption(() => creationDateDaysAgo(30));
      expect(daysBeforeDeletion.value).toBeUndefined();
    });
  });

  describe('isInAlertPeriod', () => {
    it('returns false when creationDate is undefined', () => {
      const { isInAlertPeriod } = useMeetingPeremption(() => undefined);
      expect(isInAlertPeriod.value).toBe(false);
    });

    it('returns false for a meeting less than 20 days old', () => {
      const { isInAlertPeriod } = useMeetingPeremption(() => creationDateDaysAgo(10));
      expect(isInAlertPeriod.value).toBe(false);
    });

    it('returns true for a meeting more than 20 days old', () => {
      const { isInAlertPeriod } = useMeetingPeremption(() => creationDateDaysAgo(25));
      expect(isInAlertPeriod.value).toBe(true);
    });
  });

  describe('alertType', () => {
    it('returns info when not in alert period', () => {
      const { alertType } = useMeetingPeremption(() => creationDateDaysAgo(5));
      expect(alertType.value).toBe('info');
    });

    it('returns warning when in alert period', () => {
      const { alertType } = useMeetingPeremption(() => creationDateDaysAgo(25));
      expect(alertType.value).toBe('warning');
    });
  });
});
