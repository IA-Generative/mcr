import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const { push } = vi.hoisted(() => ({ push: vi.fn() }));
const { addErrorMessage } = vi.hoisted(() => ({ addErrorMessage: vi.fn() }));
const {
  createMeetingAsync,
  startTranscription,
  uploadFile,
  transcodeToMp3,
  classifyUploadFailure,
} = vi.hoisted(() => ({
  createMeetingAsync: vi.fn(),
  startTranscription: vi.fn(),
  uploadFile: vi.fn(),
  transcodeToMp3: vi.fn(),
  classifyUploadFailure: vi.fn(),
}));

vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }));
vi.mock('@/services/http/http.utils', () => ({ classifyUploadFailure }));
vi.mock('@/composables/use-toaster', () => ({ default: () => ({ addErrorMessage }) }));
vi.mock('@/plugins/i18n', () => ({ t: (key: string) => key }));
vi.mock('@/router/routes', () => ({ ROUTES: { MEETINGS: { path: '/meetings' } } }));
vi.mock('@/composables/use-multipart', () => ({ useMultipart: () => ({ uploadFile }) }));
vi.mock('@/utils/video2audioConverter', () => ({
  useVideo2audioConverter: () => ({ transcodeToMp3 }),
}));
vi.mock('@/services/meetings/use-meeting', () => ({
  useMeetings: () => ({
    addMeetingMutation: () => ({ mutateAsync: createMeetingAsync }),
    startTranscriptionMutation: () => ({ mutate: startTranscription }),
  }),
}));

import { useImportMeeting } from './use-import-meeting';

const DURATION_SECONDS = 60;

function makeFile(name: string, type: string) {
  return new File([new Uint8Array(10)], name, { type });
}

describe('useImportMeeting.importFile', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    createMeetingAsync.mockResolvedValue({ id: 7 });
    uploadFile.mockResolvedValue(undefined);
    startTranscription.mockImplementation((_id: number, opts?: { onSuccess?: () => void }) =>
      opts?.onSuccess?.(),
    );
    transcodeToMp3.mockResolvedValue(makeFile('output.mp3', 'audio/mpeg'));
    classifyUploadFailure.mockReturnValue('unknown');

    vi.stubGlobal(
      'Audio',
      class {
        onloadedmetadata: (() => void) | null = null;
        duration = DURATION_SECONDS;
        set src(_value: string) {
          setTimeout(() => this.onloadedmetadata?.(), 0);
        }
      },
    );
    URL.createObjectURL = vi.fn(() => 'blob:fake');
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it.each([
    ['Réunion client.mp3', 'Réunion client'],
    ['nom.avec.points.wav', 'nom.avec.points'],
    ['sansextension', 'sansextension'],
  ])('derives the title from the filename without extension: %s', async (fileName, expected) => {
    const { importFile } = useImportMeeting();
    await importFile(makeFile(fileName, 'audio/mpeg'));

    expect(createMeetingAsync.mock.calls[0][0]).toMatchObject({
      name: expected,
      name_platform: 'MCR_IMPORT',
    });
  });

  it('uploads an audio file directly, then starts transcription and redirects', async () => {
    const { importFile } = useImportMeeting();
    await importFile(makeFile('meeting.m4a', 'audio/m4a'));

    expect(transcodeToMp3).not.toHaveBeenCalled();
    expect(createMeetingAsync).toHaveBeenCalledTimes(1);
    expect(uploadFile).toHaveBeenCalledTimes(1);
    expect(uploadFile).toHaveBeenCalledWith({ meetingId: 7, file: expect.any(File) });
    expect(startTranscription).toHaveBeenCalledWith(7, expect.any(Object));
    expect(push).toHaveBeenCalledWith('/meetings/7');
  });

  it('transcodes a video file and uploads the resulting mp3', async () => {
    const { importFile } = useImportMeeting();
    await importFile(makeFile('demo.mp4', 'video/mp4'));

    expect(transcodeToMp3).toHaveBeenCalledTimes(1);
    const uploadedFile = uploadFile.mock.calls[0][0].file as File;
    expect(uploadedFile.name).toMatch(/\.mp3$/);
  });

  it('still imports (without dates) when the audio metadata cannot be read', async () => {
    vi.stubGlobal(
      'Audio',
      class {
        onloadedmetadata: (() => void) | null = null;
        onerror: (() => void) | null = null;
        duration = NaN;
        set src(_value: string) {
          setTimeout(() => this.onerror?.(), 0);
        }
      },
    );

    const { importFile } = useImportMeeting();
    await importFile(makeFile('meeting.mp3', 'audio/mpeg'));

    const dto = createMeetingAsync.mock.calls[0][0];
    expect(dto.start_date).toBeUndefined();
    expect(dto.end_date).toBeUndefined();
    expect(uploadFile).toHaveBeenCalledTimes(1);
    expect(push).toHaveBeenCalledWith('/meetings/7');
  });

  it('shows a toast and creates no meeting when transcoding fails', async () => {
    transcodeToMp3.mockRejectedValue(new Error('boom'));

    const { importFile } = useImportMeeting();
    await importFile(makeFile('demo.mp4', 'video/mp4'));

    expect(addErrorMessage).toHaveBeenCalledWith('meeting.import-form.errors.file-invalid');
    expect(createMeetingAsync).not.toHaveBeenCalled();
  });

  it('shows a toast and does not upload when meeting creation fails', async () => {
    createMeetingAsync.mockRejectedValue(new Error('boom'));

    const { importFile } = useImportMeeting();
    await importFile(makeFile('meeting.mp3', 'audio/mpeg'));

    expect(addErrorMessage).toHaveBeenCalledWith('error.meeting-creation');
    expect(uploadFile).not.toHaveBeenCalled();
    expect(push).not.toHaveBeenCalled();
  });

  it('shows a toast and does not redirect when the upload fails', async () => {
    uploadFile.mockRejectedValue(new Error('boom'));

    const { importFile } = useImportMeeting();
    await importFile(makeFile('meeting.mp3', 'audio/mpeg'));

    expect(addErrorMessage).toHaveBeenCalledWith('error.file-upload');
    expect(startTranscription).not.toHaveBeenCalled();
    expect(push).not.toHaveBeenCalled();
  });

  it('shows the proxy-blocked message when the upload is classified as blocked', async () => {
    uploadFile.mockRejectedValue(new Error('boom'));
    classifyUploadFailure.mockReturnValue('blocked');

    const { importFile } = useImportMeeting();
    await importFile(makeFile('meeting.mp3', 'audio/mpeg'));

    expect(addErrorMessage).toHaveBeenCalledWith('error.file-upload-blocked');
    expect(push).not.toHaveBeenCalled();
  });

  it('derives start_date/end_date from the audio duration', async () => {
    const { importFile } = useImportMeeting();
    await importFile(makeFile('meeting.mp3', 'audio/mpeg'));

    const dto = createMeetingAsync.mock.calls[0][0];
    const start = new Date(dto.start_date).getTime();
    const end = new Date(dto.end_date).getTime();
    expect(end - start).toBe(DURATION_SECONDS * 1000);
  });
});
