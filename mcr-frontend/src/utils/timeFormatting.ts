import { t } from '@/plugins/i18n';

export function formatDurationMinutes(durationMinutes: number | undefined): string {
  if (durationMinutes === undefined) {
    return t('meeting.transcription.wait-time.computing-estimation');
  }

  const hours = Math.floor(durationMinutes / 60);
  const minutes = durationMinutes % 60;

  if (hours >= 24) {
    return t('meeting.transcription.wait-time.duration.more-than-24h');
  }

  const parts: string[] = [];
  if (hours > 0) parts.push(`${hours} h`);
  if (minutes > 0) parts.push(`${minutes} min`);

  const formattedTime = parts.join(' ');

  return t('meeting.transcription.wait-time.duration.less-than', {
    formattedTime,
  });
}

export function formatDurationLabel(durationSeconds: number): string {
  const parts: string[] = [];

  const days = Math.floor(durationSeconds / 86400);
  if (days > 0) {
    parts.push(`${days} j`);
  }

  const hours = Math.floor((durationSeconds % 86400) / 3600);
  if (hours > 0) {
    parts.push(`${hours} h`);
  }

  const minutes = Math.floor((durationSeconds % 3600) / 60);
  if (minutes > 0) {
    parts.push(`${minutes} min`);
  }

  const seconds = Math.floor(durationSeconds % 60);
  if (seconds > 0) {
    parts.push(`${seconds} s`);
  }

  return parts.length > 0 ? parts.join(' ') : '0 s';
}
