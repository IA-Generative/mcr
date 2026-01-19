import { format, isValid, parseISO } from 'date-fns';
import { fr } from 'date-fns/locale';
import sanitize from 'sanitize-filename';

export function formatMeetingDate(date: string) {
  const parsedDate = parseISO(date);

  if (!isValid(parsedDate)) {
    return '-';
  }

  return format(parsedDate, 'P - p', {
    locale: fr,
  });
}

export function sanitizeFilename(name: string) {
  return sanitize(name, { replacement: '_' }).replace(/\./g, '_');
}
