import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest';
import {
  initMultipartUploadService,
  signMultipartPartService,
  completeMultipartUploadService,
  abortMultipartUploadService,
  requestMeetingRemovalDuringUnload,
} from './meetings.service';
import HttpService from '../http/http.service';

const { getCurrentAccessToken } = vi.hoisted(() => ({ getCurrentAccessToken: vi.fn() }));

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
  API_URL: '/api',
}));
vi.mock('@/services/auth/token-provider', () => ({ getCurrentAccessToken }));

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

describe('requestMeetingRemovalDuringUnload', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    fetchMock.mockResolvedValue(undefined);
    vi.stubGlobal('fetch', fetchMock);
    getCurrentAccessToken.mockReturnValue('a-token');
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('deletes every meeting with a request the browser keeps alive past the page', () => {
    requestMeetingRemovalDuringUnload([101, 102]);

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/meetings/101', {
      method: 'DELETE',
      keepalive: true,
      headers: { Authorization: 'Bearer a-token' },
    });
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/meetings/102', {
      method: 'DELETE',
      keepalive: true,
      headers: { Authorization: 'Bearer a-token' },
    });
  });

  it('sends nothing when the session no longer holds a token', () => {
    getCurrentAccessToken.mockReturnValue(undefined);

    requestMeetingRemovalDuringUnload([101]);

    expect(fetchMock).not.toHaveBeenCalled();
  });
});
