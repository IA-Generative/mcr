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
  it('envoie les bons paramètres à HttpService.post', async () => {
    await initMultipartUploadService(1, 'audio.wav', 'audio/wav');
    expect(HttpService.post).toHaveBeenLastCalledWith('meetings/1/multipart/init', {
      filename: 'audio.wav',
      content_type: 'audio/wav',
    });
  });

  it('retourne la réponse attendue', async () => {
    await initMultipartUploadService(1, 'audio.wav', 'audio/wav');
    expect(HttpService.post).toHaveLastResolvedWith({
      data: { upload_id: 'u1', object_key: 'k1' },
    });
  });

  it('gère les erreurs de l’API', async () => {
    (HttpService.post as any).mockRejectedValueOnce(new Error('API error'));
    await expect(initMultipartUploadService(1, 'audio.wav', 'audio/wav')).rejects.toThrow(
      'API error',
    );
  });

  it('supporte contentType optionnel', async () => {
    await initMultipartUploadService(1, 'audio.wav');
    expect(HttpService.post).toHaveBeenLastCalledWith('meetings/1/multipart/init', {
      filename: 'audio.wav',
      content_type: undefined,
    });
  });
});

describe('signMultipartUploadService', () => {
  it('envoie les bons paramètres à HttpService.post', async () => {
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

  it('retourne la réponse attendue', async () => {
    await signMultipartPartService({
      meetingId: 1,
      uploadId: 'u1',
      objectKey: 'k1',
      partNumber: 1,
    });
    expect(HttpService.post).toHaveLastResolvedWith({ data: { url: 'http://www.example.com' } });
  });

  it('gère les erreurs de l’API', async () => {
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
  it('envoie les bons paramètres à HttpService.post', async () => {
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

  it('retourne la réponse attendue', async () => {
    await completeMultipartUploadService({
      meetingId: 1,
      uploadId: 'u1',
      objectKey: 'k1',
      parts: [],
    });
    expect(HttpService.post).toHaveLastResolvedWith(undefined);
  });

  it('gère les erreurs de l’API', async () => {
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
  it('envoie les bons paramètres à HttpService.post', async () => {
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

  it('retourne la réponse attendue', async () => {
    await abortMultipartUploadService({
      meetingId: 1,
      uploadId: 'u1',
      objectKey: 'k1',
    });
    expect(HttpService.post).toHaveLastResolvedWith(undefined);
  });

  it('gère les erreurs de l’API', async () => {
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
