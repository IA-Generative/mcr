import HttpService, { API_PATHS } from '../http/http.service';
import type { PaginationQuery } from '../shared/pagination.type';
import type { MultipartInitResponse, UploadTranscriptionParams } from './meetings.service.types';
import type {
  AddMeetingDto,
  MeetingDto,
  MeetingDtoWithPresignedUrl,
  Part,
  TranscriptionWaitingTimeResponse,
  UpdateMeetingDto,
} from './meetings.types';
import type { AxiosProgressEvent, AxiosResponse } from 'axios';

const DOCX_MIME_TYPE = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

export async function getAll(params: PaginationQuery): Promise<MeetingDto[]> {
  const response = await HttpService.get(API_PATHS.MEETINGS, { params });
  return response.data;
}

export async function removeOne(id: number) {
  await HttpService.delete(`${API_PATHS.MEETINGS}/${id}`);
}

export async function create(payload: AddMeetingDto): Promise<MeetingDto> {
  const { data } = await HttpService.post(`${API_PATHS.MEETINGS}`, payload);
  return data;
}

export async function createAndGetUploadUrl(
  meeting_payload: AddMeetingDto,
  filename: string,
): Promise<MeetingDtoWithPresignedUrl> {
  const payload = {
    meeting_data: meeting_payload,
    presigned_request: { filename },
  };
  const { data } = await HttpService.post(
    `${API_PATHS.MEETINGS}/create_and_generate_presigned_url`,
    payload,
  );
  return data;
}

export async function generateUploadUrl(meetingId: number, filename: string): Promise<string> {
  const payload = { filename };
  const { data } = await HttpService.post(
    `${API_PATHS.MEETINGS}/${meetingId}/presigned_url/generate`,
    payload,
  );
  return data;
}

export async function uploadFileWithPresignedUrl(url: string, file: File): Promise<void> {
  await HttpService.put(url, file, {
    transformRequest: (data, headers) => {
      delete headers['Authorization'];
      headers['Content-Type'] = file.type;
      return data;
    },
  });
}

export async function uploadMultipartPartWitPresignedUrl(
  url: string,
  blob: Blob,
): Promise<AxiosResponse> {
  return await HttpService.put(url, blob, {
    transformRequest: (data, headers) => {
      setFileHeaders(blob, headers);
      return data;
    },
  });
}

export async function update(id: number, payload: UpdateMeetingDto): Promise<MeetingDto> {
  const { data } = await HttpService.put(`${API_PATHS.MEETINGS}/${id}`, payload);
  return data;
}

export async function getOne(id: number): Promise<MeetingDto> {
  const response = await HttpService.get(`${API_PATHS.MEETINGS}/${id}`);
  return response.data;
}

export async function initCapture(id: number): Promise<void> {
  await HttpService.post(`${API_PATHS.MEETINGS}/${id}/capture/init`);
}

export async function stopCapture(id: number): Promise<void> {
  await HttpService.post(`${API_PATHS.MEETINGS}/${id}/capture/stop`);
}

export async function startTranscription(id: number): Promise<void> {
  await HttpService.post(`${API_PATHS.MEETINGS}/${id}/transcription/init`);
}

export async function generateMeetingTranscription(id: number): Promise<AxiosResponse> {
  const body = null;
  const config = {
    responseType: 'blob' as const,
    headers: {
      'Content-Type': DOCX_MIME_TYPE,
    },
  };
  const response = await HttpService.post(
    `${API_PATHS.MEETINGS}/${id}/transcription`,
    body,
    config,
  );

  return response;
}

export async function uploadTranscription({
  id,
  file,
  onProgress,
}: UploadTranscriptionParams): Promise<void> {
  const formData = new FormData();
  formData.append('file', file);

  await HttpService.put(`${API_PATHS.MEETINGS}/${id}/transcription`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent: AxiosProgressEvent) => {
      if (onProgress) {
        onProgress(progressEvent);
      }
    },
  });
}

export async function getReport(id: number): Promise<AxiosResponse> {
  const config = {
    responseType: 'blob' as const,
    headers: {
      'Content-Type': DOCX_MIME_TYPE,
    },
  };

  const response = await HttpService.get(`${API_PATHS.MEETINGS}/${id}/report`, config);
  return response;
}

export async function generateReport(id: number): Promise<void> {
  await HttpService.post(`${API_PATHS.MEETINGS}/${id}/report`);
}

export async function getTranscriptionWaitingTime(
  meeting_id: number,
): Promise<import('./meetings.types').TranscriptionWaitingTimeResponse> {
  const { data } = await HttpService.get(
    `${API_PATHS.MEETINGS}/${meeting_id}/transcription/wait-time`,
  );
  return data;
}

export async function getGlobalTranscriptionWaitingTime(): Promise<TranscriptionWaitingTimeResponse> {
  const { data } = await HttpService.get(
    `${API_PATHS.MEETINGS}/transcription/wait-time/estimation`,
  );
  return data;
}

export async function initMultipartUploadService(
  meetingId: number,
  filename: string,
  contentType?: string,
): Promise<MultipartInitResponse> {
  const payload = { filename, content_type: contentType };
  const { data } = await HttpService.post(
    `${API_PATHS.MEETINGS}/${meetingId}/multipart/init`,
    payload,
  );
  return data;
}

export async function signMultipartPartService(params: {
  meetingId: number;
  uploadId: string;
  objectKey: string;
  partNumber: number;
}): Promise<string> {
  const { meetingId, uploadId, objectKey, partNumber } = params;
  const payload = { upload_id: uploadId, object_key: objectKey, part_number: partNumber };
  const { data } = await HttpService.post(
    `${API_PATHS.MEETINGS}/${meetingId}/multipart/sign`,
    payload,
  );
  return data.url;
}

export async function completeMultipartUploadService(params: {
  meetingId: number;
  uploadId: string;
  objectKey: string;
  parts: Part[];
}): Promise<void> {
  const { meetingId, uploadId, objectKey, parts } = params;
  const payload = {
    upload_id: uploadId,
    object_key: objectKey,
    parts: parts.map((p) => ({ part_number: p.partNumber, etag: p.etag })),
  };
  await HttpService.post(`${API_PATHS.MEETINGS}/${meetingId}/multipart/complete`, payload);
}

export async function abortMultipartUploadService(params: {
  meetingId: number;
  uploadId: string;
  objectKey: string;
}): Promise<void> {
  const { meetingId, uploadId, objectKey } = params;
  const payload = { upload_id: uploadId, object_key: objectKey };
  await HttpService.post(`${API_PATHS.MEETINGS}/${meetingId}/multipart/abort`, payload);
}

export function setFileHeaders(file: Blob, headers: Record<string, string | undefined>) {
  delete headers['Authorization'];
  if (file.type) {
    headers['Content-Type'] = file.type;
  } else {
    delete headers['Content-Type'];
  }
  return headers;
}
