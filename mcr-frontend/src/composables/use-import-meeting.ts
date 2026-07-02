import { useMultipart } from '@/composables/use-multipart';
import useToaster from '@/composables/use-toaster';
import { t } from '@/plugins/i18n';
import { ROUTES } from '@/router/routes';
import type { AddImportMeetingDto } from '@/services/meetings/meetings.types';
import { classifyUploadFailure } from '@/services/http/http.utils';
import { useMeetings } from '@/services/meetings/use-meeting';
import { reportError } from '@/services/observability/sentry';
import {
  ALLOWED_IMPORT_EXTENSIONS,
  ALLOWED_IMPORT_FORMATS_LABEL,
  VIDEO_IMPORT_EXTENSIONS,
  getFileExtension,
} from '@/utils/file';
import { formatDurationLabel } from '@/utils/timeFormatting';
import { useVideo2audioConverter } from '@/utils/video2audioConverter';
import { useRouter } from 'vue-router';

const MAX_IMPORT_DURATION_SECONDS = 4 * 60 * 60;

export function useImportMeeting() {
  const router = useRouter();
  const toaster = useToaster();
  const { addMeetingMutation, startTranscriptionMutation } = useMeetings();
  const { mutateAsync: createMeetingAsync } = addMeetingMutation();
  const { mutate: startTranscription } = startTranscriptionMutation();
  const { uploadFile } = useMultipart();

  async function importFile(file: File): Promise<void> {
    const extension = getFileExtension(file)?.toLowerCase();
    if (!extension || !ALLOWED_IMPORT_EXTENSIONS.includes(extension)) {
      toaster.addErrorMessage(
        t('meeting.import.errors.file-format-unsupported', {
          formats: ALLOWED_IMPORT_FORMATS_LABEL,
        })!,
      );
      return;
    }

    const duration = await readAudioDurationSeconds(file);
    if (duration !== null && duration > MAX_IMPORT_DURATION_SECONDS) {
      toaster.addErrorMessage(
        t('meeting.import.errors.file-too-long', {
          maxDuration: formatDurationLabel(MAX_IMPORT_DURATION_SECONDS),
        })!,
      );
      return;
    }

    let audioFile = file;
    if (VIDEO_IMPORT_EXTENSIONS.includes(extension)) {
      try {
        const { transcodeToMp3 } = useVideo2audioConverter();
        audioFile = await transcodeToMp3(file);
      } catch (error) {
        reportError(error, {
          feature: 'meeting.import',
          tags: { 'import.phase': 'transcode' },
          contexts: {
            import: {
              extension,
              mimeType: file.type,
              sizeBytes: file.size,
              durationSeconds: duration,
            },
          },
        });
        toaster.addErrorMessage(t('meeting.import.errors.file-invalid')!);
        return;
      }
    }

    const dto: AddImportMeetingDto = {
      name: stripExtension(file.name),
      name_platform: 'MCR_IMPORT',
      creation_date: new Date().toISOString(),
    };

    applyDurationToDates(dto, duration);
    await uploadFileWithMultipart(dto, renameWithTimestamp(audioFile));
  }

  async function uploadFileWithMultipart(dto: AddImportMeetingDto, file: File): Promise<void> {
    let meeting;

    try {
      meeting = await createMeetingAsync(dto);
    } catch {
      toaster.addErrorMessage(t('error.meeting-creation')!);
      return;
    }

    try {
      await uploadFile({ meetingId: meeting.id, file });
    } catch (error) {
      const messageKey =
        classifyUploadFailure(error, navigator.onLine) === 'blocked'
          ? 'error.file-upload-blocked'
          : 'error.file-upload';
      toaster.addErrorMessage(t(messageKey)!);
      return;
    }

    startTranscription(meeting.id, {
      onSuccess: () => router.push(`${ROUTES.MEETINGS.path}/${meeting.id}`),
    });
  }

  return { importFile };
}

function stripExtension(fileName: string): string {
  const parts = fileName.split('.');
  return parts.length > 1 ? parts.slice(0, -1).join('.') : fileName;
}

function renameWithTimestamp(file: File): File {
  const extension = getFileExtension(file);
  return new File([file], `${Date.now()}.${extension}`, {
    type: file.type,
    lastModified: file.lastModified,
  });
}

const METADATA_READ_TIMEOUT_MS = 10_000;

function applyDurationToDates(dto: AddImportMeetingDto, duration: number | null): void {
  if (duration === null) {
    return;
  }

  const endDate = new Date();
  const startDate = new Date(endDate.getTime() - duration * 1000);

  dto.start_date = startDate.toISOString();
  dto.end_date = endDate.toISOString();
}

function readAudioDurationSeconds(file: File): Promise<number | null> {
  return new Promise((resolve) => {
    const audio = new Audio();
    const objectUrl = URL.createObjectURL(file);

    const finish = (duration: number | null) => {
      URL.revokeObjectURL(objectUrl);
      resolve(duration);
    };

    const timeoutId = setTimeout(() => finish(null), METADATA_READ_TIMEOUT_MS);

    audio.onloadedmetadata = () => {
      clearTimeout(timeoutId);
      finish(Number.isFinite(audio.duration) && audio.duration > 0 ? audio.duration : null);
    };
    audio.onerror = () => {
      clearTimeout(timeoutId);
      finish(null);
    };

    audio.src = objectUrl;
  });
}
