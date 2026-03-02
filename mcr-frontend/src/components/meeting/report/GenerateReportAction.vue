<template>
  <component
    :is="currentStateComponent"
    @on-generate="(reportType: ReportType) => onGetOrGenerateReport(reportType)"
    @on-reset="onResetReport"
  />
</template>

<script setup lang="ts">
import useToaster from '@/composables/use-toaster';
import {
  type MeetingDto,
  type MeetingStatus,
  type ReportType,
} from '@/services/meetings/meetings.types';
import { useMeetings } from '@/services/meetings/use-meeting';
import { downloadFileFromAxios } from '@/utils/file';
import { useI18n } from 'vue-i18n';
import TranscriptionNotReadyComponent from './TranscriptionNotReady.vue';
import ReportFormatSelection from './ReportFormatSelection.vue';
import ReportDownload from './ReportDownload.vue';
import ReportPending from './ReportPending.vue';
import { sanitizeFilename } from '@/utils/formatters';

const props = defineProps<{
  meeting: MeetingDto;
}>();

const toaster = useToaster();
const { t } = useI18n();

const { getReportMutation, generateReportMutation, resetReportMutation } = useMeetings();
const { mutate: generateReport } = generateReportMutation({
  onError: () => {
    toaster.addErrorMessage(t('error.report-generation')!);
  },
});
const { mutate: getReport } = getReportMutation({
  onSuccess: (response) => {
    const filename = `Compte_Rendu_${props.meeting.name}`;
    downloadFileFromAxios(response, sanitizeFilename(filename));
  },
  onError: (err) => {
    console.log(err);
    toaster.addErrorMessage(t('error.default'));
  },
});

const { mutate: resetReportStatus } = resetReportMutation();

function onResetReport() {
  resetReportStatus(props.meeting.id);
}

function onGetOrGenerateReport(reportType?: ReportType) {
  if (props.meeting.status == 'REPORT_DONE') getReport(props.meeting.id);
  else if (props.meeting.status == 'TRANSCRIPTION_DONE' && reportType)
    generateReport({ id: props.meeting.id, body: { report_types: [reportType] } });
}

const currentStateComponent = computed(() => getStateComponent(props.meeting.status));

function getStateComponent(status: MeetingStatus) {
  switch (status) {
    case 'TRANSCRIPTION_DONE':
      return ReportFormatSelection;
    case 'REPORT_DONE':
      return ReportDownload;
    case 'REPORT_PENDING':
      return ReportPending;
    default:
      return TranscriptionNotReadyComponent;
  }
}

watch(
  () => props.meeting.status,
  (newStatus, oldStatus) => {
    if (newStatus !== oldStatus && newStatus === 'REPORT_DONE') {
      getReport(props.meeting.id);
    }
  },
);
</script>
