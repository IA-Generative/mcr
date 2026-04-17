import { DELAY_TO_SHOW_ALERT, MAX_DELAY_TO_FETCH_DELIVERABLE } from '@/config/meeting';
import { differenceInDays, parseISO } from 'date-fns';

export function meetingDateIsInAlertPeriod(date: string): boolean {
  const parsedDate = parseISO(date);
  return differenceInDays(new Date(), parsedDate) > DELAY_TO_SHOW_ALERT;
}

export function getNumberOfDaysBeforeMeetingDeletion(date: string): number {
  const parsedDate = parseISO(date);
  const daysDifference = differenceInDays(new Date(), parsedDate);
  return Math.max(0, MAX_DELAY_TO_FETCH_DELIVERABLE - daysDifference);
}
