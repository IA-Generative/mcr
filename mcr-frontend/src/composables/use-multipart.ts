import { getRetryDelay, MAX_RETRIES, PART_SIZE, PUT_TIMEOUT_MS } from '@/config/meeting';
import HttpService from '@/services/http/http.service';
import {
  classifyUploadFailure,
  getAxiosCode,
  getStatusCode,
  type UploadFailureType,
} from '@/services/http/http.utils';
import { isStorageReachable } from '@/services/http/reachability';
import {
  abortMultipartUploadService,
  completeMultipartUploadService,
  initMultipartUploadService,
  setFileHeaders,
  signMultipartPartService,
} from '@/services/meetings/meetings.service';
import type { Part } from '@/services/meetings/meetings.types';
import { reportError, type ReportOptions } from '@/services/observability/sentry';
import { useMutation } from '@tanstack/vue-query';

export type UploadPhase = 'init' | 'sign' | 'put' | 'complete';

export class UploadError extends Error {
  constructor(
    readonly phase: UploadPhase,
    readonly cause: unknown,
    readonly partNumber?: number,
  ) {
    super(`${phase} failed`);
    this.name = 'UploadError';
  }
}

const uploadMutationConfig = {
  retry: MAX_RETRIES,
  retryDelay: getRetryDelay,
  meta: { skipReport: true },
} as const;

export function useMultipart() {
  // Wrap each step so a failure self-describes its phase — no mutable phase var.
  async function step<T>(
    phase: UploadPhase,
    fn: () => Promise<T>,
    partNumber?: number,
  ): Promise<T> {
    try {
      return await fn();
    } catch (cause) {
      throw new UploadError(phase, cause, partNumber);
    }
  }

  async function uploadFile(params: { meetingId: number; file: File }): Promise<void> {
    const { meetingId, file } = params;
    const startedAt = performance.now();
    const totalSize = file.size;
    const totalParts = Math.ceil(totalSize / PART_SIZE);
    const completedParts: Part[] = [];
    let bytesSent = 0;
    let uploadId: string | undefined;
    let objectKey: string | undefined;
    let lastPutUrl: string | undefined;

    try {
      const init = await step('init', () =>
        initMultipartUpload({ meetingId, fileName: file.name, fileType: file.type }),
      );
      uploadId = init.upload_id;
      objectKey = init.object_key;

      for (let partNumber = 1; partNumber <= totalParts; partNumber++) {
        const blob = getFilePartBlob(partNumber, totalSize, file);
        const url = await step(
          'sign',
          () =>
            signMultipartPart({
              meetingId,
              uploadId: init.upload_id,
              objectKey: init.object_key,
              partNumber,
            }),
          partNumber,
        );
        lastPutUrl = url;
        const etag = await step('put', () => putMultipartPart({ url, blob }), partNumber);
        completedParts.push({ partNumber, etag });
        bytesSent += blob.size;
      }

      await step('complete', () =>
        completeMultipartUpload({
          meetingId,
          uploadId: init.upload_id,
          objectKey: init.object_key,
          parts: completedParts,
        }),
      );
    } catch (error) {
      if (uploadId && objectKey) {
        // best-effort cleanup; its own failure must stay silent
        await abortMultipartUpload({ meetingId, uploadId, objectKey }).catch(() => {});
      }

      const stepError = error instanceof UploadError ? error : new UploadError('init', error);
      const online = navigator.onLine;
      const failureType = classifyUploadFailure(stepError.cause, online);

      let storageReachable = undefined;
      if (stepError.phase === 'put' && failureType === 'blocked' && lastPutUrl) {
        storageReachable = await isStorageReachable(lastPutUrl);
      }

      reportError(
        stepError,
        buildUploadReport(stepError, {
          meetingId,
          totalParts,
          fileSize: totalSize,
          bytesSent,
          durationMs: Math.round(performance.now() - startedAt),
          online,
          failureType,
          storageReachable,
        }),
      );
      throw stepError.cause instanceof Error ? stepError.cause : stepError;
    }
  }

  function buildUploadReport(
    error: UploadError,
    meta: {
      meetingId: number;
      totalParts: number;
      fileSize: number;
      bytesSent: number;
      durationMs: number;
      online: boolean;
      failureType: UploadFailureType;
      storageReachable?: boolean;
    },
  ): ReportOptions {
    const connection = (navigator as { connection?: { effectiveType?: string } }).connection;
    return {
      feature: 'meeting.upload',
      tags: {
        'meeting.id': meta.meetingId,
        'upload.phase': error.phase,
        'upload.failure_type': meta.failureType,
      },
      contexts: {
        upload: {
          phase: error.phase,
          partNumber: error.partNumber,
          totalParts: meta.totalParts,
          fileSize: meta.fileSize,
          bytesSent: meta.bytesSent,
          durationMs: meta.durationMs,
          httpStatus: getStatusCode(error.cause),
          axiosCode: getAxiosCode(error.cause),
          online: meta.online,
          effectiveType: connection?.effectiveType ?? null,
          failureType: meta.failureType,
          storageReachable: meta.storageReachable ?? null,
        },
      },
    };
  }

  function getFilePartBlob(partNumber: number, totalSize: number, file: File) {
    const start = (partNumber - 1) * PART_SIZE;
    const end = Math.min(start + PART_SIZE, totalSize);
    return file.slice(start, end);
  }

  const { mutateAsync: initMultipartUpload } = useMutation({
    mutationFn: async (params: { meetingId: number; fileName: string; fileType: string }) => {
      const { meetingId, fileName, fileType } = params;
      return await initMultipartUploadService(meetingId, fileName, fileType);
    },
    ...uploadMutationConfig,
  });

  const { mutateAsync: signMultipartPart } = useMutation({
    mutationFn: async (params: {
      meetingId: number;
      uploadId: string;
      objectKey: string;
      partNumber: number;
    }) => {
      return await signMultipartPartService(params);
    },
    ...uploadMutationConfig,
  });

  const { mutateAsync: putMultipartPart } = useMutation({
    mutationFn: async (params: { url: string; blob: Blob }) => {
      const { url, blob } = params;

      const response = await HttpService.put(url, blob, {
        timeout: PUT_TIMEOUT_MS,
        transformRequest: (data, headers) => {
          setFileHeaders(blob, headers);
          return data;
        },
      });
      const etagHeader = response.headers?.etag as string | undefined;
      if (!etagHeader) {
        throw new Error('Missing ETag header from S3 upload_part response');
      }
      return etagHeader;
    },
    ...uploadMutationConfig,
  });

  const { mutateAsync: completeMultipartUpload } = useMutation({
    mutationFn: async (params: {
      meetingId: number;
      uploadId: string;
      objectKey: string;
      parts: Part[];
    }) => {
      return await completeMultipartUploadService(params);
    },
    ...uploadMutationConfig,
  });

  const { mutateAsync: abortMultipartUpload } = useMutation({
    mutationFn: async (params: { meetingId: number; uploadId: string; objectKey: string }) => {
      return await abortMultipartUploadService(params);
    },
    ...uploadMutationConfig,
  });

  return { uploadFile };
}
