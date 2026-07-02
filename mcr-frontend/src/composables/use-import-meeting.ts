import { useMultipart } from '@/composables/use-multipart';
import useToaster from '@/composables/use-toaster';
import { t } from '@/plugins/i18n';
import { ROUTES } from '@/router/routes';
import type { AddImportMeetingDto } from '@/services/meetings/meetings.types';
import { useMeetings } from '@/services/meetings/use-meeting';
import { getFileExtension } from '@/utils/file';
import { useVideo2audioConverter } from '@/utils/video2audioConverter';
import { useRouter } from 'vue-router';

export function useImportMeeting() {
  const router = useRouter();
  const toaster = useToaster();
  const { addMeetingMutation, startTranscriptionMutation } = useMeetings();
  const { mutateAsync: createMeetingAsync } = addMeetingMutation();
  const { mutate: startTranscription } = startTranscriptionMutation();
  const { uploadFile } = useMultipart();

  async function importFile(file: File): Promise<void> {
    let audioFile = file;
    if (file.type.startsWith('video/')) {
      try {
        const { transcodeToMp3 } = useVideo2audioConverter();
        audioFile = await transcodeToMp3(file);
      } catch {
        toaster.addErrorMessage(t('meeting.import-form.errors.file-invalid')!);
        return;
      }
    }

    const dto: AddImportMeetingDto = {
      name: stripExtension(file.name),
      name_platform: 'MCR_IMPORT',
      creation_date: new Date().toISOString(),
    };

    const dtoWithDates = await updateDtoWithDates(dto, audioFile);
    await uploadFileWithMultipart(dtoWithDates, renameWithTimestamp(audioFile));
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
    } catch {
      toaster.addErrorMessage(t('error.file-upload')!);
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

async function updateDtoWithDates(
  dto: AddImportMeetingDto,
  file: File,
): Promise<AddImportMeetingDto> {
  const audio = new Audio();
  audio.src = URL.createObjectURL(file);
  await new Promise((resolve) => (audio.onloadedmetadata = resolve));
  const duration = audio.duration;

  const endDate = new Date(Date.now());
  const startDate = new Date(endDate.getTime() - duration * 1000);
  dto.start_date = startDate.toISOString();
  dto.end_date = endDate.toISOString();

  return dto;
}
