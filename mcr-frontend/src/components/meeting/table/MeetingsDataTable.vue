<template>
  <div class="fr-container flex flex-col">
    <DsfrDataTable
      title=""
      :headers-row="headers"
      no-caption
      :rows="rows"
      :sortable-rows="['date', 'title']"
      class="mb-2"
    >
      <template #header="{ key, label }">
        <div class="w-full flex gap-1 items-center">
          {{ label }}
          <DsfrTooltip
            v-if="key === 'report'"
            :content="t('meetings_v2.table.columns.report.tooltip')"
          >
          </DsfrTooltip>
        </div>
      </template>

      <template #cell="{ colKey, cell }">
        <MeetingCellDispatcher
          :col-key="colKey as ColKey"
          :cell="cell as CellMap[ColKey]"
        />
      </template>
    </DsfrDataTable>
    <DsfrPagination
      v-model:current-page="currentPageIndex"
      class="self-center mb-6"
      :pages="pages"
      :prev-page-title="$t('meetings.table.pagination.previous')"
      :next-page-title="$t('meetings.table.pagination.next')"
    />
  </div>
</template>

<script setup lang="ts">
import { t } from '@/plugins/i18n';
import { formatMeetingDate } from '@/utils/formatters';
import { useMeetings } from '@/services/meetings/use-meeting';
import { usePagination } from '@/composables/use-pagination';
import useToaster from '@/composables/use-toaster';
import type { CellMap, ColKey } from './types';

const toaster = useToaster();

const headers = [
  { key: 'date', label: t('meetings_v2.table.columns.date'), headerAttrs: { class: 'w-48' } },
  { key: 'title', label: t('meetings_v2.table.columns.title.label'), headerAttrs: { class: '' } },
  {
    key: 'transcription',
    label: t('meetings_v2.table.columns.transcription'),
    headerAttrs: { class: 'w-32' },
  },
  {
    key: 'report',
    label: t('meetings_v2.table.columns.report.label'),
    headerAttrs: { class: 'w-40' },
  },
  {
    key: 'actions',
    label: t('meetings_v2.table.columns.actions'),
    headerAttrs: { class: 'w-24' },
  },
];

const PAGE_SIZE = 10;

const { currentPage, setCurrentPage } = usePagination({ currentPage: 1 });

const { getAllMeetingsQuery } = useMeetings();

const { data: paginatedMeetings, error: meetingsError } = getAllMeetingsQuery({
  search: ref(''),
  page: currentPage,
  pageSize: ref(PAGE_SIZE),
});

const meetings = computed(() => paginatedMeetings.value?.data ?? []);
const totalPages = computed(() => paginatedMeetings.value?.total_pages ?? 1);

const currentPageIndex = computed({
  get: () => currentPage.value - 1,
  set: (index: number) => setCurrentPage(index + 1),
});

const pages = computed(() =>
  Array.from({ length: totalPages.value }, (_, i) => ({
    href: '',
    label: String(i + 1),
    title: `Page ${i + 1}`,
  })),
);

const rows = computed(() =>
  meetings.value.map((meeting) => ({
    date: formatMeetingDate(meeting.creation_date),
    title: {
      name: meeting.name,
      id: meeting.id,
      creation_date: meeting.creation_date,
    },
    transcription: meeting.status,
    report: meeting.status,
    actions: meeting,
  })),
);

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
:deep() .fr-table__content td {
  max-width: 10rem;
  overflow-x: hidden;
  text-overflow: ellipsis;
}
</style>
