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

export function formatRoundedDurationMinutes(durationMinutes: number | undefined): string {
  const roundedDuration =
    durationMinutes !== undefined ? roundUpToNearestTen(durationMinutes) : undefined;

  return formatDurationMinutes(roundedDuration);
}

function roundUpToNearestTen(durationMinutes: number): number {
  return Math.ceil(durationMinutes / 10) * 10;
}
