<template>
  <div class="fr-container flex flex-col">
    <DsfrDataTable
      title=""
      :headers-row="headers"
      no-caption
      :rows="rows"
      :sortable-rows="['date', 'title']"
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
        <DataTableCellsAction
          :col-key="colKey"
          :cell="cell"
        />
      </template>
    </DsfrDataTable>
    <TablePagination
      class="self-end"
      :current-page="currentPage"
      :page-size="pageSize"
      :total-pages="totalPages"
      @on-page-change="setCurrentPage"
      @on-page-size-change="setPageSize"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { t } from '@/plugins/i18n';
import { formatMeetingDate } from '@/utils/formatters';
import { useMeetings } from '@/services/meetings/use-meeting';
import { usePagination } from '@/composables/use-pagination';
import useToaster from '@/composables/use-toaster';

const toaster = useToaster();

const headers = [
  { key: 'date', label: t('meetings_v2.table.columns.date'), headerAttrs: { class: 'w-[20%]' } },
  { key: 'title', label: t('meetings_v2.table.columns.title'), headerAttrs: { class: 'w-[35%]' } },
  {
    key: 'transcription',
    label: t('meetings_v2.table.columns.transcription'),
    headerAttrs: { class: 'w-[15%]' },
  },
  {
    key: 'report',
    label: t('meetings_v2.table.columns.report.label'),
    headerAttrs: { class: 'w-[20%]' },
  },
  {
    key: 'actions',
    label: t('meetings_v2.table.columns.actions'),
    headerAttrs: { class: 'w-[10%]' },
  },
];

const { currentPage, pageSize, setCurrentPage, setPageSize } = usePagination({
  currentPage: 1,
  pageSize: 10,
});

const { getAllMeetingsQuery } = useMeetings();

const { data: paginatedMeetings, error: meetingsError } = getAllMeetingsQuery({
  search: ref(''),
  page: currentPage,
  pageSize,
});

const meetings = computed(() => paginatedMeetings.value?.data ?? []);
const totalPages = computed(() => paginatedMeetings.value?.total_pages ?? 1);

const rows = computed(() =>
  meetings.value.map((meeting) => ({
    date: formatMeetingDate(meeting.creation_date),
    title: { name: meeting.name, id: meeting.id },
    transcription: '',
    report: '',
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
