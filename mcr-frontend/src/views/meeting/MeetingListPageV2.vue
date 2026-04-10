<template>
  <div class="fr-container py-5 flex w-full flex-col gap-10">
    <PageFrontMatterV2
      :title="$t('meetings_v2.hero.title')"
      :subtitle="$t('meetings_v2.hero.subtitle')"
    />

    <div class="tile-container">
      <DsfrTile
        class="tile"
        :horizontal="true"
        :small="true"
        :img-src="videoSvgPath"
        :title="t('meetings_v2.tile-import.title')"
        :description="t('meetings_v2.tile-import.subtitle')"
      />
      <DsfrTile
        class="tile"
        :horizontal="true"
        :small="true"
        :img-src="podcastSvgPath"
        :title="t('meetings_v2.tile-record.title')"
        :description="t('meetings_v2.tile-record.subtitle')"
      />
      <DsfrTile
        class="tile"
        :horizontal="true"
        :small="true"
        :img-src="selfTrainingSvgPath"
        :title="t('meetings_v2.tile-visio.title')"
        :description="
          isWebexEnabled
            ? t('meetings_v2.tile-visio.subtitle-with-webex')
            : t('meetings_v2.tile-visio.subtitle-without-webex')
        "
      />
    </div>
  </div>

  <div class="w-full bg-[--blue-france-975-75]">
    <div class="fr-container py-5 flex w-full flex-col gap-10">
      <PageFrontMatterV2
        :title="$t('meetings_v2.table.new-title')"
        :subtitle="$t('meetings_v2.table.new-subtitle')"
      />
      <DsfrAlert
        v-if="showAlert"
        type="info"
        closeable
        data-testid="alert-availability"
        role="alertInfo"
        @close="closeAlert"
      >
        <p>
          {{ $t('meetings_v2.availability-alert-description.audio') }}
          <span style="font-weight: bold">
            {{ MAX_DELAY_TO_FETCH_AUDIO }}
            {{ $t('meetings_v2.availability-alert-description.days') }}
          </span>
        </p>
        <p>
          {{ $t('meetings_v2.availability-alert-description.pre-warning-pre-bold') }}
          <span style="font-weight: bold">
            {{ MAX_DELAY_TO_FETCH_DELIVERABLE }}
            {{ $t('meetings_v2.availability-alert-description.days') }}
          </span>
          {{ $t('meetings_v2.availability-alert-description.pre-warning-post-bold') }}
          <span
            class="fr-icon-warning-line"
            aria-hidden="true"
            style="color: var(--blue-france-sun-113-625)"
          ></span>
          {{ $t('meetings_v2.availability-alert-description.post-warning') }}
        </p>
      </DsfrAlert>
    </div>

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
          <RouterLink
            v-if="colKey === 'title'"
            :to="`${ROUTES.MEETINGS.path}/${asTitleCell(cell).id}`"
          >
            {{ asTitleCell(cell).name }}
          </RouterLink>
          <TableActions
            v-else-if="colKey === 'actions'"
            :on-delete="() => deleteMeetingModal(asMeeting(cell).id)"
            :on-edit="() => editMeetingModal(asMeeting(cell).id)"
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
  </div>
</template>

<script lang="ts" setup>
import PageFrontMatterV2 from '@/components/core/PageFrontMatterV2.vue';
import { useFeatureFlag } from '@/composables/use-feature-flag';
import { t } from '@/plugins/i18n';
import videoSvgPath from '@dsfr-artwork/pictograms/leisure/video.svg?url';
import podcastSvgPath from '@dsfr-artwork/pictograms/leisure/podcast.svg?url';
import selfTrainingSvgPath from '@dsfr-artwork/pictograms/digital/self-training.svg?url';
import useToaster from '@/composables/use-toaster';

const isWebexEnabled = useFeatureFlag('webex');
import { ref, onMounted, computed, watch } from 'vue';
import { formatMeetingDate } from '@/utils/formatters';
import { MAX_DELAY_TO_FETCH_AUDIO, MAX_DELAY_TO_FETCH_DELIVERABLE } from '@/config/meeting';
import { useMeetings } from '@/services/meetings/use-meeting';
import { RouterLink } from 'vue-router';
import { ROUTES } from '@/router/routes';
import type { MeetingDto, UpdateMeetingDto } from '@/services/meetings/meetings.types';
import { useModal } from 'vue-final-modal';
import EditMeetingModal from '@/components/meeting/modals/EditMeetingModal.vue';
import DeleteMeetingModal from '@/components/meeting/modals/DeleteMeetingModal.vue';
import TableActions from '@/components/table/TableActions.vue';
import TablePagination from '@/components/table/TablePagination.vue';
import { useI18n } from 'vue-i18n';
import { usePagination } from '@/composables/use-pagination';

const SESSION_KEY = 'dsfr-alert-closed';
const showAlert = ref(true);
const CLOSED_ALERT_VALUE = 'CLOSED_ALERT';

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

const rows = computed(() =>
  meetings.value.map((meeting) => ({
    date: formatMeetingDate(meeting.creation_date),
    title: { name: meeting.name, id: meeting.id },
    transcription: '',
    report: '',
    actions: meeting,
  })),
);
const search = ref<string>('');

const { currentPage, pageSize, setCurrentPage, setPageSize } = usePagination({
  currentPage: 1,
  pageSize: 10,
});

const { t: tI18n } = useI18n();
const { getAllMeetingsQuery, updateMeetingMutation, deleteMeetingMutation } = useMeetings();
const { mutate: updateMeeting } = updateMeetingMutation();
const { mutate: deleteMeeting } = deleteMeetingMutation();

// Type casting in functions to avoid repeating it in the template
function asTitleCell(cell: unknown): { name: string; id: number } {
  return cell as { name: string; id: number };
}
function asMeeting(cell: unknown): MeetingDto {
  return cell as MeetingDto;
}

// Code for actions modals : EDIT and DELETE
function editMeetingModal(id: number) {
  const meeting = meetings.value.find((m) => m.id === id);
  const { open } = useModal({
    component: EditMeetingModal,
    attrs: {
      itemSelected: meeting,
      onUpdateMeeting: (values: UpdateMeetingDto) => updateMeeting({ id, payload: values }),
    },
  });
  open();
}
function deleteMeetingModal(id: number) {
  const { open } = useModal({
    component: DeleteMeetingModal,
    attrs: {
      title: tI18n('meeting.confirm-delete.title'),
      onSuccess: () => deleteMeeting(id),
    },
  });
  open();
}

const { data: paginatedMeetings, error: meetingsError } = getAllMeetingsQuery({
  search,
  page: currentPage,
  pageSize,
});

const meetings = computed(() => paginatedMeetings.value?.data ?? []);

const totalPages = computed(() => paginatedMeetings.value?.total_pages ?? 1);

onMounted(() => {
  const alreadyClosed = sessionStorage.getItem(SESSION_KEY);
  if (alreadyClosed && alreadyClosed == CLOSED_ALERT_VALUE) {
    showAlert.value = false;
  }
});

function closeAlert() {
  showAlert.value = false;
  sessionStorage.setItem(SESSION_KEY, CLOSED_ALERT_VALUE);
}

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
.tile-container {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.tile {
  width: 95vw;
  height: 20vh;
}

@media (min-width: 440px) {
  .tile {
    width: 95vw;
    height: 15vh;
  }
}

@media (min-width: 1040px) {
  .tile-container {
    flex-direction: row;
  }

  .tile {
    width: 30vw;
    height: 20vh;
  }
}
</style>
