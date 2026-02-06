import { describe, it, expect, vi } from 'vitest';
import {
  initMultipartUploadService,
  signMultipartPartService,
  completeMultipartUploadService,
  abortMultipartUploadService,
} from './meetings.service';
import HttpService from '../http/http.service';

vi.mock('../http/http.service', () => ({
  default: {
    post: vi.fn(async (url: string) => {
      if (url.includes('/init')) {
        return { data: { upload_id: 'u1', object_key: 'k1' } };
      }

      if (url.includes('/sign')) {
        return { data: { url: 'http://www.example.com' } };
      }

      return;
    }),
  },
  API_PATHS: {
    MEETINGS: 'meetings',
  },
}));

describe('initMultipartUploadService', () => {
  it('HttpService.post called with correct attributes', async () => {
    await initMultipartUploadService(1, 'audio.wav', 'audio/wav');
    expect(HttpService.post).toHaveBeenLastCalledWith('meetings/1/multipart/init', {
      filename: 'audio.wav',
      content_type: 'audio/wav',
    });
  });

  it('returns the expected value', async () => {
    await initMultipartUploadService(1, 'audio.wav', 'audio/wav');
    expect(HttpService.post).toHaveLastResolvedWith({
      data: { upload_id: 'u1', object_key: 'k1' },
    });
  });

  it('handles API errors', async () => {
    (HttpService.post as any).mockRejectedValueOnce(new Error('API error'));
    await expect(initMultipartUploadService(1, 'audio.wav', 'audio/wav')).rejects.toThrow(
      'API error',
    );
  });

  it('handles optional contentType', async () => {
    await initMultipartUploadService(1, 'audio.wav');
    expect(HttpService.post).toHaveBeenLastCalledWith('meetings/1/multipart/init', {
      filename: 'audio.wav',
      content_type: undefined,
    });
  });
});

describe('signMultipartUploadService', () => {
  it('HttpService.post called with correct attributes', async () => {
    await signMultipartPartService({
      meetingId: 1,
      uploadId: 'u1',
      objectKey: 'k1',
      partNumber: 1,
    });
    expect(HttpService.post).toHaveBeenLastCalledWith('meetings/1/multipart/sign', {
      upload_id: 'u1',
      object_key: 'k1',
      part_number: 1,
    });
  });

  it('returns the expected value', async () => {
    await signMultipartPartService({
      meetingId: 1,
      uploadId: 'u1',
      objectKey: 'k1',
      partNumber: 1,
    });
    expect(HttpService.post).toHaveLastResolvedWith({ data: { url: 'http://www.example.com' } });
  });

  it('handles API errors', async () => {
    (HttpService.post as any).mockRejectedValueOnce(new Error('API error'));
    await expect(
      signMultipartPartService({
        meetingId: 1,
        uploadId: 'u1',
        objectKey: 'k1',
        partNumber: 1,
      }),
    ).rejects.toThrow('API error');
  });
});

describe('completeMultipartUploadService', () => {
  it('HttpService.post called with correct attributes', async () => {
    await completeMultipartUploadService({
      meetingId: 1,
      uploadId: 'u1',
      objectKey: 'k1',
      parts: [],
    });
    expect(HttpService.post).toHaveBeenLastCalledWith('meetings/1/multipart/complete', {
      upload_id: 'u1',
      object_key: 'k1',
      parts: [],
    });
  });

  it('returns the expected value', async () => {
    await completeMultipartUploadService({
      meetingId: 1,
      uploadId: 'u1',
      objectKey: 'k1',
      parts: [],
    });
    expect(HttpService.post).toHaveLastResolvedWith(undefined);
  });

  it('handles API errors', async () => {
    (HttpService.post as any).mockRejectedValueOnce(new Error('API error'));
    await expect(
      completeMultipartUploadService({
        meetingId: 1,
        uploadId: 'u1',
        objectKey: 'k1',
        parts: [],
      }),
    ).rejects.toThrow('API error');
  });
});

describe('abortMultipartUploadService', () => {
  it('HttpService.post called with correct attributes', async () => {
    await abortMultipartUploadService({
      meetingId: 1,
      uploadId: 'u1',
      objectKey: 'k1',
    });
    expect(HttpService.post).toHaveBeenLastCalledWith('meetings/1/multipart/abort', {
      upload_id: 'u1',
      object_key: 'k1',
    });
  });

  it('returns the expected value', async () => {
    await abortMultipartUploadService({
      meetingId: 1,
      uploadId: 'u1',
      objectKey: 'k1',
    });
    expect(HttpService.post).toHaveLastResolvedWith(undefined);
  });

  it('handles API errors', async () => {
    (HttpService.post as any).mockRejectedValueOnce(new Error('API error'));
    await expect(
      abortMultipartUploadService({
        meetingId: 1,
        uploadId: 'u1',
        objectKey: 'k1',
      }),
    ).rejects.toThrow('API error');
  });
});
