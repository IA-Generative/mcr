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

const MEETING_TITLE_MAX_LENGTH = 30;
const EMPTY_TITLE_FALLBACK = 'Sans_Titre';

export function buildDeliverableFilename(typeLabel: string, meetingName: string): string {
  const withUnderscores = meetingName.replace(/\s+/g, '_');
  const sanitized = sanitizeFilename(withUnderscores).slice(0, MEETING_TITLE_MAX_LENGTH);
  const titlePart = sanitized.length > 0 ? sanitized : EMPTY_TITLE_FALLBACK;
  return `${typeLabel}_${titlePart}.docx`;
}
