import { getRetryDelay, MAX_RETRIES, PART_SIZE } from '@/config/meeting';
import HttpService from '@/services/http/http.service';
import {
  abortMultipartUploadService,
  completeMultipartUploadService,
  initMultipartUploadService,
  setFileHeaders,
  signMultipartPartService,
} from '@/services/meetings/meetings.service';
import type { Part } from '@/services/meetings/meetings.types';
import { useMutation } from '@tanstack/vue-query';
import useToaster from './use-toaster';
import { t } from '@/plugins/i18n';

const toaster = useToaster();

export function useMultipart() {
  async function uploadFile(params: { meetingId: number; file: File }): Promise<void> {
    const { meetingId, file } = params;

    const { upload_id: uploadId, object_key: objectKey } = await initMultipartUpload({
      meetingId: meetingId,
      fileName: file.name,
      fileType: file.type,
    });

    const totalSize = file.size;
    const totalParts = Math.ceil(totalSize / PART_SIZE);
    const completedParts: Part[] = [];

    for (let partNumber = 1; partNumber <= totalParts; partNumber++) {
      const blob = getFilePartBlob(partNumber, totalSize, file);
      await uploadMultipartPart(
        {
          meetingId: meetingId,
          uploadId,
          objectKey,
          partNumber,
          blob,
        },
        {
          onSuccess: (etagHeader) => {
            completedParts.push({ partNumber, etag: etagHeader });
          },
          onError: async () => {
            await abortMultipartUpload({ meetingId: meetingId, uploadId, objectKey });
            toaster.addErrorMessage(t('error.file-upload')!);
            throw new Error('Failed to upload file');
          },
        },
      );
    }

    await completeMultipartUpload({
      meetingId: meetingId,
      uploadId,
      objectKey,
      parts: completedParts,
    });
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
    onError: () => {
      throw new Error('Failed to upload file');
    },
    retry: MAX_RETRIES,
    retryDelay: (attemptIndex) => getRetryDelay(attemptIndex),
  });

  const { mutateAsync: uploadMultipartPart } = useMutation({
    mutationFn: async (params: {
      meetingId: number;
      uploadId: string;
      objectKey: string;
      partNumber: number;
      blob: Blob;
    }) => {
      const { meetingId, uploadId, objectKey, partNumber, blob } = params;

      const url = await signMultipartPartService({
        meetingId,
        uploadId,
        objectKey,
        partNumber,
      });

      const response = await HttpService.put(url, blob, {
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
    retry: MAX_RETRIES,
    retryDelay: (attemptIndex) => getRetryDelay(attemptIndex),
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
    onError: () => {
      throw new Error('Failed to upload file');
    },
    retry: MAX_RETRIES,
    retryDelay: (attemptIndex) => getRetryDelay(attemptIndex),
  });

  const { mutateAsync: abortMultipartUpload } = useMutation({
    mutationFn: async (params: { meetingId: number; uploadId: string; objectKey: string }) => {
      return await abortMultipartUploadService(params);
    },
    onError: () => {
      throw new Error('Failed to upload file');
    },
    retry: MAX_RETRIES,
    retryDelay: (attemptIndex) => getRetryDelay(attemptIndex),
  });

  return { uploadFile };
}
