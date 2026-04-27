import { DELAY_TO_SHOW_ALERT, MAX_DELAY_TO_FETCH_DELIVERABLE } from '@/config/meeting';
import { differenceInDays, parseISO } from 'date-fns';
import type { MeetingDetailDto } from './meetings.types';
import { logger } from '@sentry/vue';

export function meetingDateIsInAlertPeriod(date: string): boolean {
  const parsedDate = parseISO(date);
  return differenceInDays(new Date(), parsedDate) > DELAY_TO_SHOW_ALERT;
}

export function getNumberOfDaysBeforeMeetingDeletion(date: string): number {
  const parsedDate = parseISO(date);
  const daysDifference = differenceInDays(new Date(), parsedDate);
  return Math.max(0, MAX_DELAY_TO_FETCH_DELIVERABLE - daysDifference);
}

export function getCalendarDateFromIso8601(isoDate: string): string {
  // Output format : DD/MM/YY
  const date = new Date(isoDate);

  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0'); // getMonth() commence à 0
  const year = String(date.getFullYear()).slice(-2);

  return `${day}/${month}/${year}`;
}

export function getTimeFromIso8601(isoDate: string): string {
  // Output format : HHhMM
  const date = new Date(isoDate);

  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');

  return `${hours}h${minutes}`;
}

export function getMeetingDuration(meeting: MeetingDetailDto): string {
  if (meeting.start_date === undefined || meeting.end_date === undefined) {
    logger.error(
      'Meeting duration cannot be computed if meeting start_date or end_date is missing',
    );
    return '';
  } else {
    const diffMs = new Date(meeting.end_date).getTime() - new Date(meeting.start_date).getTime();

    const totalSeconds = Math.floor(diffMs / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    return [hours, minutes, seconds].map((v) => String(v).padStart(2, '0')).join(':');
  }
}
