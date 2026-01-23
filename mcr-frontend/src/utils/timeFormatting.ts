import { t } from '@/plugins/i18n';

export function formatDurationMinutes(durationMinutes: number | undefined): string {
  if (durationMinutes === undefined) {
    return t('meeting.transcription.transcription-in-queue.computing-estimation');
  }

  const hours = Math.floor(durationMinutes / 60);
  const minutes = durationMinutes % 60;

  if (hours >= 24) {
    return t('meeting.transcription.transcription-in-queue.duration.more-than-24h');
  }

  const parts: string[] = [];
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}min`);

  const formattedTime = parts.join(' ');

  return t('meeting.transcription.transcription-in-queue.duration.less-than', {
    formattedTime,
  });
}
