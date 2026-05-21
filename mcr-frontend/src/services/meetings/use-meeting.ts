import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query';
import {
  create,
  generateMeetingTranscription,
  generateUploadUrl,
  getAll,
  getOne,
  initCapture,
  removeOne,
  startTranscription,
  stopCapture,
  update,
  uploadFileWithPresignedUrl,
} from './meetings.service';
import { QUERY_KEYS } from '@/plugins/vue-query';
import type {
  AddMeetingDto,
  MeetingDetailDto,
  MeetingDto,
  MeetingStatus,
  UpdateMeetingDto,
} from './meetings.types';
import { type Ref } from 'vue';
import type { ExtraMutationOptions } from '@/utils/types';
import useToaster from '@/composables/use-toaster';
import { t } from '@/plugins/i18n';
import { lookupComu, lookupComuByPasscode } from '../lookup/lookup.service';
import throttle from 'lodash.throttle';

const POLLING_INTERVAL = 10 * 1000; // 10 seconds
const THROTTLING_INTERVAL = 200; // 200 milliseconds
const STOP_CAPTURE_SKIPPED = Symbol('STOP_CAPTURE_SKIPPED');

const throttledGetAll = throttle(getAll, THROTTLING_INTERVAL, { leading: true, trailing: true });

function getAllMeetingsQuery(params: {
  search?: Ref<string | undefined>;
  page: Ref<number>;
  pageSize: Ref<number>;
}) {
  return useQuery({
    queryKey: [QUERY_KEYS.MEETINGS, params.search, params.page, params.pageSize],
    queryFn: () =>
      throttledGetAll({
        search: params.search?.value,
        page: params.page.value,
        page_size: params.pageSize.value,
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
    data.status === 'CAPTURE_IN_PROGRESS' ||
    data.status === 'CAPTURE_DONE' ||
    data.status === 'TRANSCRIPTION_PENDING' ||
    data.status === 'TRANSCRIPTION_IN_PROGRESS' ||
    data.status === 'REPORT_PENDING'
  );
}

function deleteMeetingMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      await queryClient.cancelQueries({ queryKey: [QUERY_KEYS.MEETINGS, id] });
      return removeOne(id);
    },
    onSuccess: (_, id) => {
      queryClient.removeQueries({ queryKey: [QUERY_KEYS.MEETINGS, id] });
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
      queryClient.setQueryData([QUERY_KEYS.MEETINGS, id], (old: MeetingDto | undefined) =>
        old ? updateMeetingStatus(old, 'CAPTURE_PENDING') : undefined,
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

function updateMeetingOptimistically() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: UpdateMeetingDto }) => update(id, payload),
    onSuccess: (data, { id }) => {
      queryClient.setQueryData([QUERY_KEYS.MEETINGS, id], (old: MeetingDetailDto | undefined) =>
        old ? { ...old, notes: data.notes } : undefined,
      );
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
  });
}

const throttledLookupComu = throttle(lookupComu, THROTTLING_INTERVAL, {
  leading: true,
  trailing: true,
});

const throttledLookupComuByPasscode = throttle(lookupComuByPasscode, THROTTLING_INTERVAL, {
  leading: true,
  trailing: true,
});

function lookupMeetingUrlMutation(options?: ExtraMutationOptions<typeof lookupComu>) {
  return useMutation({
    mutationFn: throttledLookupComu,
    ...options,
  });
}

function lookupMeetingByPasscodeMutation(
  options?: ExtraMutationOptions<typeof lookupComuByPasscode>,
) {
  return useMutation({
    mutationFn: throttledLookupComuByPasscode,
    ...options,
  });
}

export function useMeetings() {
  return {
    getMeetingQuery,
    getAllMeetingsQuery,
    addMeetingMutation,
    deleteMeetingMutation,
    updateMeetingMutation,
    updateMeetingOptimistically,
    startCaptureMutation,
    stopCaptureMutation,
    startTranscriptionMutation,
    downloadMutation,
    uploadFileWithPresignedUrlMutation,
    lookupMeetingUrlMutation,
    lookupMeetingByPasscodeMutation,
  };
}
