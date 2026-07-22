import { UploadAbortedError, useMultipart } from '@/composables/use-multipart';
import useToaster from '@/composables/use-toaster';
import { useUploadBatchWriter, type UploadDraft } from '@/composables/use-upload-batch';
import { useUploadStatus } from '@/composables/use-upload-status';
import { t } from '@/plugins/i18n';
import { classifyUploadFailure, type UploadFailureType } from '@/services/http/http.utils';
import type { AddImportMeetingDto } from '@/services/meetings/meetings.types';
import { useMeetings } from '@/services/meetings/use-meeting';
import { reportError } from '@/services/observability/sentry';
import {
  ALLOWED_IMPORT_EXTENSIONS,
  ALLOWED_IMPORT_FORMATS_LABEL,
  MAX_IMPORT_DURATION_SECONDS,
  VIDEO_IMPORT_EXTENSIONS,
  getFileExtension,
} from '@/utils/file';
import { ROUTES } from '@/router/routes';
import { formatDurationLabel } from '@/utils/timeFormatting';
import { useVideo2audioConverter } from '@/utils/video2audioConverter';
import { useRouter } from 'vue-router';

type Orchestrator = { importFiles: (files: File[]) => Promise<void> };

type ItemRuntime = {
  file: File;
  controller: AbortController;
  stopTranscoding?: () => void;
  registryId: number;
};

type ValidatedFile = { file: File; draft: UploadDraft };

const runtimes = new Map<number, ItemRuntime>();
const startedUploads = new Set<number>();
const startedTranscodes = new Set<number>();

export function useImportMeeting(): Orchestrator {
  const router = useRouter();
  const toaster = useToaster();
  const { addMeetingMutation, startTranscriptionMutation } = useMeetings();
  const { mutateAsync: createMeetingAsync } = addMeetingMutation();
  const { mutate: startTranscription } = startTranscriptionMutation();
  const { uploadFile } = useMultipart();
  const { registerUpload, unregisterUpload } = useUploadStatus();
  const writer = useUploadBatchWriter();

  async function importFiles(files: File[]): Promise<void> {
    const candidates = await Promise.all(files.map(validateFile));
    const validated = candidates.filter((candidate): candidate is ValidatedFile => !!candidate);
    if (validated.length === 0) {
      return;
    }
    sortByAscendingDuration(validated);

    const itemIds = writer.enqueue(validated.map((candidate) => candidate.draft));
    itemIds.forEach((id, index) => {
      const controller = new AbortController();
      const runtime: ItemRuntime = { file: validated[index].file, controller, registryId: 0 };
      runtime.registryId = registerUpload({
        abort: () => {
          controller.abort();
          runtime.stopTranscoding?.();
          forget(id);
          writer.clearAll();
        },
      });
      runtimes.set(id, runtime);
    });

    pump();
    await createMeetingsSequentially(itemIds);
  }

  async function validateFile(file: File): Promise<ValidatedFile | null> {
    const extension = getFileExtension(file)?.toLowerCase();
    if (!extension || !ALLOWED_IMPORT_EXTENSIONS.includes(extension)) {
      toaster.addErrorMessage(
        t('meeting.import.errors.file-format-unsupported', {
          formats: ALLOWED_IMPORT_FORMATS_LABEL,
        })!,
      );

      return null;
    }

    const durationSeconds = await readAudioDurationSeconds(file);
    if (durationSeconds !== null && durationSeconds > MAX_IMPORT_DURATION_SECONDS) {
      toaster.addErrorMessage(
        t('meeting.import.errors.file-too-long', {
          maxDuration: formatDurationLabel(MAX_IMPORT_DURATION_SECONDS),
        })!,
      );

      return null;
    }

    return {
      file,
      draft: {
        title: stripExtension(file.name),
        kind: VIDEO_IMPORT_EXTENSIONS.includes(extension) ? 'video' : 'audio',
        durationSeconds,
        totalBytes: file.size,
      },
    };
  }

  async function createMeetingsSequentially(itemIds: number[]): Promise<void> {
    for (const id of itemIds) {
      const item = writer.getItem(id);
      if (!runtimes.has(id) || !item) {
        continue;
      }

      const dto: AddImportMeetingDto = {
        name: item.title,
        name_platform: 'MCR_IMPORT',
        creation_date: new Date().toISOString(),
      };
      applyDurationToDates(dto, item.durationSeconds);

      try {
        const meeting = await createMeetingAsync(dto);
        if (!runtimes.has(id)) {
          continue;
        }
        writer.attachMeeting(id, meeting.id);
        pump();
      } catch (error) {
        const failureType = classifyUploadFailure(error, navigator.onLine);
        reportError(error, {
          feature: 'meeting.import',
          tags: { 'import.phase': 'meeting-creation', 'import.failure_type': failureType },
        });
        settleAsFailed(id, failureType);
      }
    }
  }

  function pump(): void {
    for (const item of writer.getTranscodingItems()) {
      if (!startedTranscodes.has(item.id)) {
        startedTranscodes.add(item.id);
        void runTranscode(item.id);
      }
    }
    for (const item of writer.getUploadingItems()) {
      if (!startedUploads.has(item.id)) {
        startedUploads.add(item.id);
        void runUpload(item.id);
      }
    }
  }

  async function runTranscode(id: number): Promise<void> {
    const runtime = runtimes.get(id);
    if (!runtime) {
      return;
    }

    const elapsed = createSampleClock();
    const converter = useVideo2audioConverter((ratio) =>
      writer.recordTranscodeProgress(id, ratio, elapsed()),
    );
    runtime.stopTranscoding = converter.stopTranscoding;

    try {
      const mp3 = await converter.transcodeToMp3(runtime.file);
      if (!runtimes.has(id)) {
        return;
      }
      runtime.file = mp3;
      writer.finishTranscode(id, mp3.size);
      pump();
    } catch (error) {
      if (!runtimes.has(id)) {
        return;
      }

      const failureType: UploadFailureType = 'http-client';
      reportError(error, {
        feature: 'meeting.import',
        tags: { 'import.phase': 'transcode', 'import.failure_type': failureType },
        contexts: {
          import: {
            extension: getFileExtension(runtime.file),
            mimeType: runtime.file.type,
            sizeBytes: runtime.file.size,
            durationSeconds: writer.getItem(id)?.durationSeconds ?? null,
          },
        },
      });
      settleAsFailed(id, failureType);
    } finally {
      runtime.stopTranscoding = undefined;
    }
  }

  async function runUpload(id: number): Promise<void> {
    const runtime = runtimes.get(id);
    const item = writer.getItem(id);
    if (!runtime || !item || item.meetingId === null) {
      return;
    }

    const elapsed = createSampleClock();
    try {
      await uploadFile({
        meetingId: item.meetingId,
        file: renameWithTimestamp(runtime.file, id),
        signal: runtime.controller.signal,
        onProgress: (sentBytes) => writer.recordProgress(id, sentBytes, elapsed()),
      });
      if (!runtimes.has(id)) {
        return;
      }
      writer.complete(id);
      startTranscription(item.meetingId);
      const soleItem = writer.isSoleItem(id);
      settle(id);
      pump();
      if (soleItem) {
        redirectToMeeting(item.meetingId);
      }
    } catch (error) {
      if (error instanceof UploadAbortedError || !runtimes.has(id)) {
        return;
      }

      settleAsFailed(id, classifyUploadFailure(error, navigator.onLine));
    }
  }

  function redirectToMeeting(meetingId: number): void {
    writer.clearAll();
    void router.push(`${ROUTES.MEETINGS.path}/${meetingId}`);
  }

  function settle(id: number): void {
    const runtime = runtimes.get(id);
    if (!runtime) {
      return;
    }
    unregisterUpload(runtime.registryId);
    forget(id);
  }

  function forget(id: number): void {
    runtimes.delete(id);
    startedTranscodes.delete(id);
    startedUploads.delete(id);
  }

  function settleAsFailed(id: number, failureType: UploadFailureType): void {
    writer.fail(id, failureType);

    const runtime = runtimes.get(id);
    if (runtime) {
      runtime.controller.abort();
      runtime.stopTranscoding?.();
    }
    settle(id);
    pump();
  }

  return { importFiles };
}

function createSampleClock(): () => number {
  let last: number | null = null;
  return () => {
    const now = performance.now();
    const seconds = last === null ? 0 : (now - last) / 1000;
    last = now;
    return seconds;
  };
}

function sortByAscendingDuration(files: ValidatedFile[]): void {
  files.sort((a, b) => {
    if (a.draft.durationSeconds === null || b.draft.durationSeconds === null) {
      return Number(a.draft.durationSeconds === null) - Number(b.draft.durationSeconds === null);
    }
    return a.draft.durationSeconds - b.draft.durationSeconds;
  });
}

function stripExtension(fileName: string): string {
  const parts = fileName.split('.');
  return parts.length > 1 ? parts.slice(0, -1).join('.') : fileName;
}

function renameWithTimestamp(file: File, itemId: number): File {
  const extension = getFileExtension(file);
  return new File([file], `${Date.now()}-${itemId}.${extension}`, {
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
