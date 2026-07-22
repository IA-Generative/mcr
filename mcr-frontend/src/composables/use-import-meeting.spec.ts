import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { addErrorMessage } = vi.hoisted(() => ({ addErrorMessage: vi.fn() }));
const { reportError } = vi.hoisted(() => ({ reportError: vi.fn() }));
const {
  createMeetingAsync,
  startTranscription,
  uploadFile,
  transcodeToMp3,
  stopTranscoding,
  classifyUploadFailure,
  registerUpload,
  unregisterUpload,
  registeredAborts,
  push,
} = vi.hoisted(() => ({
  createMeetingAsync: vi.fn(),
  startTranscription: vi.fn(),
  uploadFile: vi.fn(),
  transcodeToMp3: vi.fn(),
  stopTranscoding: vi.fn(),
  classifyUploadFailure: vi.fn(),
  registerUpload: vi.fn(),
  unregisterUpload: vi.fn(),
  registeredAborts: [] as (() => void)[],
  push: vi.fn(),
}));

vi.mock('@/services/observability/sentry', () => ({ reportError }));
vi.mock('@/services/http/http.utils', () => ({ classifyUploadFailure }));
vi.mock('@/composables/use-toaster', () => ({ default: () => ({ addErrorMessage }) }));
vi.mock('@/plugins/i18n', () => ({ t: (key: string) => key }));
vi.mock('@/composables/use-multipart', () => {
  class UploadAbortedError extends Error {}
  return { useMultipart: () => ({ uploadFile }), UploadAbortedError };
});
vi.mock('@/composables/use-upload-status', () => ({
  useUploadStatus: () => ({ registerUpload, unregisterUpload }),
}));
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }));
vi.mock('@/router/routes', () => ({ ROUTES: { MEETINGS: { path: '/meetings' } } }));
vi.mock('@/utils/video2audioConverter', () => ({
  useVideo2audioConverter: () => ({ transcodeToMp3, stopTranscoding }),
}));
vi.mock('@/services/meetings/use-meeting', () => ({
  useMeetings: () => ({
    addMeetingMutation: () => ({ mutateAsync: createMeetingAsync }),
    startTranscriptionMutation: () => ({ mutate: startTranscription }),
  }),
}));

const fileDurations = new Map<string, number | null>();

function makeFile(
  name: string,
  { type = 'audio/mpeg', duration = 60 as number | null, bytes = 10 } = {},
): File {
  fileDurations.set(name, duration);
  return new File([new Uint8Array(bytes)], name, { type });
}

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (error: unknown) => void;
};

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function deferCalls<T>(mock: ReturnType<typeof vi.fn>): Deferred<T>[] {
  const pending: Deferred<T>[] = [];
  mock.mockImplementation(() => {
    const call = deferred<T>();
    pending.push(call);
    return call.promise;
  });
  return pending;
}

async function flush(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0));
  await new Promise((resolve) => setTimeout(resolve, 0));
}

async function setup() {
  const { useImportMeeting } = await import('./use-import-meeting');
  const { useUploadBatch } = await import('./use-upload-batch');
  const { UploadAbortedError } = await import('./use-multipart');
  return { ...useImportMeeting(), batch: useUploadBatch(), UploadAbortedError };
}

describe('useImportMeeting.importFiles', () => {
  let nextMeetingId: number;

  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    registeredAborts.length = 0;
    fileDurations.clear();
    nextMeetingId = 101;

    registerUpload.mockImplementation((upload: { abort: () => void }) => {
      registeredAborts.push(upload.abort);
      return registeredAborts.length;
    });
    createMeetingAsync.mockImplementation(async () => ({ id: nextMeetingId++ }));
    uploadFile.mockResolvedValue(undefined);
    transcodeToMp3.mockResolvedValue(makeMp3());
    classifyUploadFailure.mockReturnValue('unknown');

    vi.stubGlobal(
      'Audio',
      class {
        onloadedmetadata: (() => void) | null = null;
        onerror: (() => void) | null = null;
        duration = 0;
        set src(value: string) {
          const duration = fileDurations.get(value.replace('blob:', ''));
          setTimeout(() => {
            if (duration === null || duration === undefined) {
              this.onerror?.();
            } else {
              this.duration = duration;
              this.onloadedmetadata?.();
            }
          }, 0);
        }
      },
    );
    URL.createObjectURL = vi.fn((file: File) => `blob:${file.name}`);
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function makeMp3(): File {
    return new File([new Uint8Array(20)], 'output.mp3', { type: 'audio/mpeg' });
  }

  it('creates one meeting per selected file, sequentially, titled by the filename without extension', async () => {
    const creations = deferCalls<{ id: number }>(createMeetingAsync);
    const { importFiles } = await setup();

    const run = importFiles([
      makeFile('Réunion client.mp3'),
      makeFile('nom.avec.points.wav', { type: 'audio/wav' }),
    ]);
    await flush();

    expect(createMeetingAsync).toHaveBeenCalledTimes(1);
    expect(createMeetingAsync.mock.calls[0][0]).toMatchObject({
      name: 'Réunion client',
      name_platform: 'MCR_IMPORT',
    });

    creations[0].resolve({ id: 101 });
    await flush();
    expect(createMeetingAsync).toHaveBeenCalledTimes(2);
    expect(createMeetingAsync.mock.calls[1][0]).toMatchObject({ name: 'nom.avec.points' });

    creations[1].resolve({ id: 102 });
    await run;
  });

  it('derives the meeting dates from the audio duration read at selection', async () => {
    const { importFiles } = await setup();
    await importFiles([makeFile('meeting.mp3', { duration: 60 })]);
    await flush();

    const dto = createMeetingAsync.mock.calls[0][0];
    expect(new Date(dto.end_date).getTime() - new Date(dto.start_date).getTime()).toBe(60_000);
  });

  it('only starts uploading a file once its own meeting exists', async () => {
    const creations = deferCalls<{ id: number }>(createMeetingAsync);
    const { importFiles } = await setup();

    const run = importFiles([
      makeFile('a.mp3', { duration: 60 }),
      makeFile('b.mp3', { duration: 120 }),
    ]);
    await flush();
    expect(uploadFile).not.toHaveBeenCalled();

    creations[0].resolve({ id: 101 });
    await flush();
    expect(uploadFile).toHaveBeenCalledTimes(1);
    expect(uploadFile.mock.calls[0][0].meetingId).toBe(101);

    creations[1].resolve({ id: 102 });
    await run;
  });

  it('creates meetings then uploads one file at a time, shortest first regardless of selection order', async () => {
    const uploads = deferCalls<void>(uploadFile);
    const { importFiles } = await setup();

    await importFiles([
      makeFile('long.mp3', { duration: 300 }),
      makeFile('short.mp3', { duration: 60 }),
      makeFile('medium.mp3', { duration: 120 }),
    ]);
    await flush();

    expect(createMeetingAsync.mock.calls.map((call) => call[0].name)).toEqual([
      'short',
      'medium',
      'long',
    ]);
    expect(uploadFile).toHaveBeenCalledTimes(1);
    expect(uploadFile.mock.calls[0][0].meetingId).toBe(101);

    uploads[0].resolve();
    await flush();
    expect(uploadFile.mock.calls[1][0].meetingId).toBe(102);

    uploads[1].resolve();
    await flush();
    expect(uploadFile.mock.calls[2][0].meetingId).toBe(103);
    uploads[2].resolve();
  });

  it('transcodes a video while another file uploads', async () => {
    deferCalls<void>(uploadFile);
    deferCalls<File>(transcodeToMp3);
    const { importFiles } = await setup();

    await importFiles([
      makeFile('audio.mp3', { duration: 60 }),
      makeFile('video.mp4', { duration: 120, type: 'video/mp4' }),
    ]);
    await flush();

    expect(uploadFile).toHaveBeenCalledTimes(1);
    expect(transcodeToMp3).toHaveBeenCalledTimes(1);
  });

  it('uploads the transcoded mp3 to the video meeting once its turn comes', async () => {
    const transcodes = deferCalls<File>(transcodeToMp3);
    const { importFiles, batch } = await setup();

    await importFiles([makeFile('video.mp4', { duration: 120, type: 'video/mp4' })]);
    await flush();

    transcodes[0].resolve(makeMp3());
    await flush();

    expect(uploadFile).toHaveBeenCalledTimes(1);
    const uploaded = uploadFile.mock.calls[0][0];
    expect(uploaded.meetingId).toBe(101);
    expect((uploaded.file as File).name).toMatch(/^\d+-\d+\.mp3$/);
    expect(push).toHaveBeenCalledWith('/meetings/101');
    expect(batch.items.value).toHaveLength(0);
  });

  it('a meeting-creation failure settles that file only; the others upload and transcribe', async () => {
    createMeetingAsync.mockImplementation(async (dto: { name: string }) => {
      if (dto.name === 'bad') {
        throw new Error('boom');
      }
      return { id: nextMeetingId++ };
    });
    const { importFiles, batch } = await setup();

    await importFiles([
      makeFile('ok-1.mp3', { duration: 60 }),
      makeFile('bad.mp3', { duration: 120 }),
      makeFile('ok-2.mp3', { duration: 180 }),
    ]);
    await flush();

    expect(addErrorMessage).toHaveBeenCalledWith('error.meeting-creation');
    const byTitle = Object.fromEntries(batch.items.value.map((item) => [item.title, item]));
    expect(byTitle['bad']).toMatchObject({ status: 'error', failureType: 'unknown' });
    expect(byTitle['ok-1'].status).toBe('done');
    expect(byTitle['ok-2'].status).toBe('done');
    expect(startTranscription).toHaveBeenCalledTimes(2);
  });

  it('an upload failure shows the existing toast, settles that file and lets the next one start', async () => {
    uploadFile.mockRejectedValueOnce(new Error('boom'));
    const { importFiles, batch } = await setup();

    await importFiles([
      makeFile('fails.mp3', { duration: 60 }),
      makeFile('passes.mp3', { duration: 120 }),
    ]);
    await flush();

    expect(addErrorMessage).toHaveBeenCalledWith('error.file-upload');
    const byTitle = Object.fromEntries(batch.items.value.map((item) => [item.title, item]));
    expect(byTitle['fails']).toMatchObject({ status: 'error', failureType: 'unknown' });
    expect(byTitle['passes'].status).toBe('done');
    expect(startTranscription).toHaveBeenCalledTimes(1);
    expect(startTranscription).toHaveBeenCalledWith(102);
  });

  it('shows the proxy-blocked message when the upload failure is classified as blocked', async () => {
    uploadFile.mockRejectedValue(new Error('boom'));
    classifyUploadFailure.mockReturnValue('blocked');
    const { importFiles } = await setup();

    await importFiles([makeFile('meeting.mp3')]);
    await flush();

    expect(addErrorMessage).toHaveBeenCalledWith('error.file-upload-blocked');
  });

  it('a transcode failure is reported, toasted, and marked unprocessable without any upload', async () => {
    transcodeToMp3.mockRejectedValue(new Error('bad codec'));
    const { importFiles, batch } = await setup();

    await importFiles([makeFile('demo.mp4', { duration: 60, type: 'video/mp4' })]);
    await flush();

    expect(reportError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({ feature: 'meeting.import' }),
    );
    expect(addErrorMessage).toHaveBeenCalledWith('meeting.import.errors.file-invalid');
    expect(batch.items.value[0]).toMatchObject({ status: 'error', failureType: 'http-client' });
    expect(uploadFile).not.toHaveBeenCalled();
  });

  it('stops an in-flight transcode when the meeting creation of its file fails', async () => {
    deferCalls<File>(transcodeToMp3);
    createMeetingAsync.mockRejectedValue(new Error('boom'));
    const { importFiles, batch } = await setup();

    await importFiles([makeFile('video.mp4', { duration: 120, type: 'video/mp4' })]);
    await flush();

    expect(stopTranscoding).toHaveBeenCalledTimes(1);
    expect(batch.items.value[0].status).toBe('error');
  });

  it('starts the transcription of each completed file', async () => {
    const { importFiles } = await setup();

    await importFiles([makeFile('meeting.mp3')]);
    await flush();

    expect(startTranscription).toHaveBeenCalledTimes(1);
    expect(startTranscription.mock.calls[0]).toEqual([101]);
  });

  it('redirects to the meeting page and clears the sticky when the sole file completes', async () => {
    const { importFiles, batch } = await setup();

    await importFiles([makeFile('solo.mp3', { duration: 60 })]);
    await flush();

    expect(push).toHaveBeenCalledWith('/meetings/101');
    expect(batch.items.value).toHaveLength(0);
  });

  it('does not redirect when a second batch joined the store meanwhile', async () => {
    const uploads = deferCalls<void>(uploadFile);
    const { importFiles } = await setup();

    await importFiles([makeFile('first.mp3', { duration: 60 })]);
    await flush();
    await importFiles([makeFile('second.mp3', { duration: 120 })]);
    await flush();

    uploads[0].resolve();
    await flush();

    expect(push).not.toHaveBeenCalled();
  });

  it('does not redirect when the sole file fails to upload', async () => {
    uploadFile.mockRejectedValueOnce(new Error('boom'));
    const { importFiles, batch } = await setup();

    await importFiles([makeFile('solo.mp3', { duration: 60 })]);
    await flush();

    expect(push).not.toHaveBeenCalled();
    expect(batch.items.value[0]).toMatchObject({ status: 'error' });
  });

  it.each([
    ['notes.txt', 'text/plain', 'meeting.import.errors.file-format-unsupported'],
    ['sansextension', 'audio/mpeg', 'meeting.import.errors.file-format-unsupported'],
  ])(
    'rejects an unsupported file (%s) at selection, before it enters the queue',
    async (name, type, key) => {
      deferCalls<void>(uploadFile);
      const { importFiles, batch } = await setup();

      await importFiles([makeFile(name, { type }), makeFile('ok.mp3')]);
      await flush();

      expect(addErrorMessage).toHaveBeenCalledWith(key);
      expect(batch.items.value).toHaveLength(1);
      expect(batch.items.value[0].title).toBe('ok');
    },
  );

  it('rejects a file longer than 4 hours at selection', async () => {
    const { importFiles, batch } = await setup();

    await importFiles([makeFile('marathon.mp3', { duration: 4 * 60 * 60 + 1 })]);
    await flush();

    expect(addErrorMessage).toHaveBeenCalledWith('meeting.import.errors.file-too-long');
    expect(batch.items.value).toHaveLength(0);
    expect(createMeetingAsync).not.toHaveBeenCalled();
  });

  it('still imports a file whose duration cannot be read, without meeting dates', async () => {
    const { importFiles, batch } = await setup();

    await importFiles([makeFile('mystery.mp3', { duration: null })]);
    await flush();

    const dto = createMeetingAsync.mock.calls[0][0];
    expect(dto.start_date).toBeUndefined();
    expect(dto.end_date).toBeUndefined();
    expect(startTranscription).toHaveBeenCalledWith(101);
    expect(batch.items.value).toHaveLength(0);
  });

  it('imports a video whose MIME type is empty, based on its extension', async () => {
    const { importFiles } = await setup();

    await importFiles([makeFile('demo.mp4', { duration: 60, type: '' })]);
    await flush();

    expect(transcodeToMp3).toHaveBeenCalledTimes(1);
  });

  it('touches neither the queue nor the navigation guard when every file is invalid', async () => {
    const { importFiles, batch } = await setup();

    await importFiles([
      makeFile('a.txt', { type: 'text/plain' }),
      makeFile('b.txt', { type: 'text/plain' }),
    ]);
    await flush();

    expect(batch.items.value).toHaveLength(0);
    expect(batch.hasActiveWork.value).toBe(false);
    expect(registerUpload).not.toHaveBeenCalled();
  });

  it('registers each file with the navigation guard at enqueue and releases it when it settles', async () => {
    uploadFile.mockRejectedValueOnce(new Error('boom'));
    const { importFiles } = await setup();

    await importFiles([
      makeFile('fails.mp3', { duration: 60 }),
      makeFile('passes.mp3', { duration: 120 }),
    ]);
    await flush();

    expect(registerUpload).toHaveBeenCalledTimes(2);
    expect(unregisterUpload).toHaveBeenCalledTimes(2);
  });

  it('a global abort stops every in-flight work and empties the queue silently', async () => {
    const uploads = deferCalls<void>(uploadFile);
    const transcodes = deferCalls<File>(transcodeToMp3);
    const { importFiles, batch, UploadAbortedError } = await setup();

    await importFiles([
      makeFile('audio.mp3', { duration: 60 }),
      makeFile('video.mp4', { duration: 120, type: 'video/mp4' }),
    ]);
    await flush();
    const uploadSignal = uploadFile.mock.calls[0][0].signal as AbortSignal;

    registeredAborts.forEach((abort) => abort());
    uploads[0].reject(new UploadAbortedError());
    transcodes[0].reject(new Error('Transcoding failed: called FFmpeg.terminate()'));
    await flush();

    expect(uploadSignal.aborted).toBe(true);
    expect(stopTranscoding).toHaveBeenCalled();
    expect(batch.items.value).toHaveLength(0);
    expect(batch.hasActiveWork.value).toBe(false);
    expect(addErrorMessage).not.toHaveBeenCalled();
    expect(reportError).not.toHaveBeenCalled();
  });

  it('a global abort while files are still queued empties the queue and stops creating meetings', async () => {
    const creations = deferCalls<{ id: number }>(createMeetingAsync);
    const { importFiles, batch } = await setup();

    const run = importFiles([
      makeFile('a.mp3', { duration: 60 }),
      makeFile('b.mp3', { duration: 120 }),
    ]);
    await flush();
    expect(createMeetingAsync).toHaveBeenCalledTimes(1);

    registeredAborts.forEach((abort) => abort());
    creations[0].resolve({ id: 101 });
    await run;
    await flush();

    expect(createMeetingAsync).toHaveBeenCalledTimes(1);
    expect(batch.items.value).toHaveLength(0);
    expect(uploadFile).not.toHaveBeenCalled();
  });

  it('a shorter file from a second selection uploads before a longer file already waiting', async () => {
    const uploads = deferCalls<void>(uploadFile);
    const { importFiles } = await setup();

    await importFiles([
      makeFile('running.mp3', { duration: 300 }),
      makeFile('waiting.mp3', { duration: 600 }),
    ]);
    await flush();
    expect(uploadFile).toHaveBeenCalledTimes(1);

    await importFiles([makeFile('quick.mp3', { duration: 60 })]);
    await flush();
    expect(uploadFile).toHaveBeenCalledTimes(1);

    uploads[0].resolve();
    await flush();
    expect(uploadFile.mock.calls[1][0].meetingId).toBe(103);

    uploads[1].resolve();
    await flush();
    expect(uploadFile.mock.calls[2][0].meetingId).toBe(102);
    uploads[2].resolve();
  });
});
