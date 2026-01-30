import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query';
import {
  create,
  createAndGetUploadUrl,
  generateMeetingTranscription,
  generateReport,
  generateUploadUrl,
  getAll,
  getOne,
  getReport,
  getTranscriptionWaitingTime,
  initCapture,
  removeOne,
  startTranscription,
  stopCapture,
  update,
  uploadFileWithPresignedUrl,
  uploadTranscription,
} from './meetings.service';
import { QUERY_KEYS } from '@/plugins/vue-query';
import type {
  AddImportMeetingDtoAndFile,
  AddMeetingDto,
  MeetingDto,
  MeetingStatus,
  UpdateMeetingDto,
} from './meetings.types';
import { type Ref } from 'vue';
import type { ExtraMutationOptions } from '@/utils/types';
import useToaster from '@/composables/use-toaster';
import { t } from '@/plugins/i18n';
import { lookupComu } from '../lookup/lookup.service';
import throttle from 'lodash.throttle';
import { BASE_BACKOFF_MS, MAX_DELAY, MAX_RETRIES } from '@/config/meeting';
import { TRANSCRIPTION_WAITING_TIME_POLLING_INTERVAL } from '@/config/meeting';

const POLLING_INTERVAL = 10 * 1000; // 10 seconds
const THROTTLING_INTERVAL = 200; // 200 milliseconds
const STOP_CAPTURE_SKIPPED = Symbol('STOP_CAPTURE_SKIPPED');

const throttledGetAll = throttle(getAll, THROTTLING_INTERVAL, { leading: true, trailing: true });

function getAllMeetingsQuery(search?: Ref<string | undefined>) {
  return useQuery({
    queryKey: [QUERY_KEYS.MEETINGS, search],
    queryFn: () =>
      throttledGetAll({
        search: search?.value,
      }),
  });
}

function getMeetingQuery(id: number) {
  return useQuery({
    queryKey: [QUERY_KEYS.MEETINGS, id],
    queryFn: () => getOne(id),
    refetchInterval: (query) =>
      shouldPollServerForUpdates(query.state.data) ? POLLING_INTERVAL : false,
  });
}

function shouldPollServerForUpdates(data?: MeetingDto): boolean {
  return (
    !data ||
    data.status === 'CAPTURE_PENDING' ||
    data.status === 'CAPTURE_BOT_IS_CONNECTING' ||
    data.status === 'CAPTURE_BOT_CONNECTION_FAILED' ||
    data.status === 'CAPTURE_DONE' ||
    data.status === 'TRANSCRIPTION_PENDING' ||
    data.status === 'TRANSCRIPTION_IN_PROGRESS' ||
    data.status === 'REPORT_PENDING'
  );
}

function deleteMeetingMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => removeOne(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.MEETINGS] });
    },
  });
}

function addMeetingMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (values: AddMeetingDto) => create(values),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.MEETINGS] }),
  });
}

function importMeetingMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (values: AddImportMeetingDtoAndFile) => {
      const meetingWithPresignedUrl = await createAndGetUploadUrl(values.dto, values.file.name);
      await uploadFileWithPresignedUrl(meetingWithPresignedUrl.presigned_url, values.file);
      return meetingWithPresignedUrl;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.MEETINGS] });
    },
  });
}

function updateMeetingMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: UpdateMeetingDto }) => update(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEYS.MEETINGS],
      });
    },
  });
}

function startCaptureMutation() {
  const queryClient = useQueryClient();
  const toaster = useToaster();

  return useMutation({
    mutationFn: (id: number) => initCapture(id),
    onSuccess: (_, id) => {
      queryClient.setQueryData([QUERY_KEYS.MEETINGS, id], (old: MeetingDto) =>
        updateMeetingStatus(old, 'CAPTURE_PENDING'),
      );
    },
    onError: () => {
      toaster.addErrorMessage(t('error.audio-capture')!);
    },
  });
}

function stopCaptureMutation() {
  const queryClient = useQueryClient();
  const toaster = useToaster();

  return useMutation({
    mutationFn: async (id: number) => {
      const meeting = await queryClient.fetchQuery({
        queryKey: [QUERY_KEYS.MEETINGS, id],
        queryFn: () => getOne(id),
      });

      if (meeting.status !== 'CAPTURE_IN_PROGRESS') {
        throw STOP_CAPTURE_SKIPPED;
      }

      return stopCapture(id);
    },
    onSuccess: (_, id) => {
      queryClient.setQueryData([QUERY_KEYS.MEETINGS, id], (old: MeetingDto) =>
        updateMeetingStatus(old, 'CAPTURE_DONE'),
      );
    },
    onError: (err: unknown) => {
      if (err === STOP_CAPTURE_SKIPPED) {
        return;
      }
      toaster.addErrorMessage(t('error.audio-capture')!);
    },
  });
}

function startTranscriptionMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => startTranscription(id),
    onSuccess: (_, id) => {
      console.log('setting meeting to TRANSCRIPTION_PENDING', id);
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.MEETINGS, id] });
    },
  });
}

function downloadMutation(options?: ExtraMutationOptions<typeof generateMeetingTranscription>) {
  return useMutation({
    mutationFn: (id: number) => generateMeetingTranscription(id),
    ...options,
  });
}

function uploadMutation(options?: ExtraMutationOptions<typeof uploadTranscription>) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, file }: { id: number; file: File }) => uploadTranscription({ id, file }),
    ...options,
    onSuccess: (data, variables, context) => {
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEYS.MEETINGS, variables.id],
      });

      options?.onSuccess?.(data, variables, context);
    },
  });
}

function getReportMutation(options?: ExtraMutationOptions<typeof getReport>) {
  return useMutation({
    mutationFn: (id: number) => getReport(id),
    ...options,
  });
}

function generateReportMutation(options?: ExtraMutationOptions<typeof generateReport>) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => generateReport(id),
    ...options,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEYS.MEETINGS, id],
      });
    },
  });
}

function updateMeetingStatus(meeting: MeetingDto, status: MeetingStatus): MeetingDto {
  return {
    ...meeting,
    status,
  };
}

type MeetingIdAndFile = {
  meetingId: number;
  file: File;
};

function uploadFileWithPresignedUrlMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (values: MeetingIdAndFile) => {
      const presigned_url = await generateUploadUrl(values.meetingId, values.file.name);
      return uploadFileWithPresignedUrl(presigned_url, values.file);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.MEETINGS] });
    },
    retry: MAX_RETRIES,
    retryDelay: (attemptIndex) => Math.min(BASE_BACKOFF_MS * 2 ** attemptIndex, MAX_DELAY),
  });
}

const throttledLookupComu = throttle(lookupComu, THROTTLING_INTERVAL, {
  leading: true,
  trailing: true,
});

function lookupMeetingUrlMutation(options?: ExtraMutationOptions<typeof lookupComu>) {
  return useMutation({
    mutationFn: throttledLookupComu,
    ...options,
  });
}

function getMeetingTranscriptionWaitTime(id: number) {
  return useQuery({
    queryKey: [QUERY_KEYS.TRANSCRIPTION_WAIT_TIME, id],
    queryFn: () => getTranscriptionWaitingTime(id),
    refetchInterval: TRANSCRIPTION_WAITING_TIME_POLLING_INTERVAL,
  });
}

export function useMeetings() {
  return {
    getMeetingQuery,
    getAllMeetingsQuery,
    addMeetingMutation,
    importMeetingMutation,
    deleteMeetingMutation,
    updateMeetingMutation,
    startCaptureMutation,
    stopCaptureMutation,
    startTranscriptionMutation,
    downloadMutation,
    uploadMutation,
    uploadFileWithPresignedUrlMutation,
    getReportMutation,
    generateReportMutation,
    lookupMeetingUrlMutation,
    getMeetingTranscriptionWaitTime,
  };
}
