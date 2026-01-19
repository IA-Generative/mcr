<template>
  <div class="fr-container py-5 flex w-full flex-col gap-10">
    <div
      v-if="globalTranscriptionWaitingTimeGreaterThan24Hours"
      class="fr-alert fr-alert--warning"
    >
      <h3 class="fr-alert__title">
        {{ $t('meetings.waiting-time-warning-title') }}
      </h3>
      <p>
        {{ $t('meetings.waiting-time-warning-description') }}
        <span class="font-bold">{{
          formatDurationMinutes(globalTranscriptionWaitingTime?.estimation_duration_minutes)
        }}</span>
      </p>
    </div>

    <PageFrontMatter
      :title="$t('meetings.table.title')"
      :subtitle="$t('meetings.subtitle')"
    />

    <div class="flex flex-col">
      <TableHeaderActions v-model="search" />
      <DsfrTable
        title=""
        :headers="[
          {
            text: t('meetings.table.columns.status'),
            headerAttrs: { class: 'w-[25%]' },
          },
          {
            text: t('meetings.table.columns.title'),
            headerAttrs: { class: 'w-full' },
          },
          {
            text: t('meetings.table.columns.date'),
            headerAttrs: { class: 'w-[30%]' },
          },
          {
            text: t('meetings.table.columns.actions'),
            headerAttrs: { class: 'w-[30%]' },
          },
        ]"
        no-caption
      >
        <TableRows
          :is-pending="areMeetingsLoading"
          :meetings="meetings"
        />
      </DsfrTable>
      <TablePagination
        class="self-end"
        :current-page="currentPage"
        :page-size="pageSize"
        :total-pages="totalPages"
        @on-page-change="setCurrentPage"
        @on-page-size-change="setPageSize"
      ></TablePagination>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { usePagination } from '@/composables/use-pagination';
import { useMeetings } from '@/services/meetings/use-meeting';
import useToaster from '@/composables/use-toaster';
import { getGlobalTranscriptionWaitingTime } from '@/services/meetings/meetings.service';
import { useQuery } from '@tanstack/vue-query';
import { formatDurationMinutes } from '@/utils/timeFormatting';
import {
  getTranscriptionQueueWarningThreshold,
  TRANSCRIPTION_WAITING_TIME_POLLING_INTERVAL,
} from '@/config/meeting';

const { t } = useI18n();
const toaster = useToaster();

const search = ref<string>('');

const { getAllMeetingsQuery } = useMeetings();
const {
  data: meetings,
  isLoading: areMeetingsLoading,
  error: meetingsError,
} = getAllMeetingsQuery(search);

const { data: globalTranscriptionWaitingTime } = useQuery({
  queryKey: ['global-transcription-waiting-time'],
  queryFn: () => getGlobalTranscriptionWaitingTime(),
  refetchInterval: TRANSCRIPTION_WAITING_TIME_POLLING_INTERVAL,
});
const globalTranscriptionWaitingTimeGreaterThan24Hours = computed(() => {
  return (
    (globalTranscriptionWaitingTime.value?.estimation_duration_minutes ?? 0) >=
    getTranscriptionQueueWarningThreshold()
  );
});

const { currentPage, totalPages, pageSize, setCurrentPage, setPageSize } = usePagination({
  currentPage: 1,
  pageSize: 10,
});

watch(
  meetingsError,
  (error) => {
    if (error) {
      toaster.addErrorMessage(t('error.meetings-loading'));
    }
  },
  { immediate: true },
);
</script>

<style scoped>
:deep(th),
:deep(td) {
  white-space: nowrap;
}

:deep(.fr-table > table) {
  table-layout: fixed;
  display: table;
}
</style>
