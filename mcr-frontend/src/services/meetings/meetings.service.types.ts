import type { AxiosProgressEvent } from 'axios';

export type UploadTranscriptionParams = {
  id: number;
  file: File;
  onProgress?: (progressEvent: AxiosProgressEvent) => void;
};

export type MultipartInitResponse = {
  upload_id: string;
  object_key: string;
};

export type UploadMultipartPartParam = {
  meetingId: number;
  uploadId: string;
  objectKey: string;
  partNumber: number;
  blob: Blob;
};
