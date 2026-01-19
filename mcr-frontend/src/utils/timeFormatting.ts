import { t } from '@/plugins/i18n';

export function formatDurationMinutes(durationMinutes: number | undefined): string {
  if (durationMinutes === undefined) {
    return t('meeting.transcription.transcription-in-queue.computing-estimation');
  }

  if (durationMinutes <= 60) {
    return t('meeting.transcription.transcription-generation-in-progress.less-than-1-hour');
  }

  const hours = Math.floor(durationMinutes / 60);
  const minutes = durationMinutes % 60;

  if (hours >= 24) {
    return `${hours} heures`;
  }

  return minutes < 10 ? `${hours}h0${minutes}` : `${hours}h${minutes}`;
}
