<template>
  <div class="bg-white p-6 flex flex-col gap-4 border border-[var(--grey-975-75-hover)]">
    <h2 class="text-blue-france-sun font-bold text-2xl">
      {{ $t('meeting-v2.deliverable-card.title') }}
    </h2>
    <p class="text-[var(--text-default-grey)] m-0">
      {{ $t('meeting-v2.deliverable-card.description') }}
    </p>

    <DsfrRadioButtonSet
      v-model="selectedType"
      name="deliverable-type"
      :options="radioOptions"
      @update:model-value="onSelectType"
    />

    <HoverTooltip
      v-if="generateBlockedByPending"
      :content="$t('meeting-v2.deliverable-card.tooltip.pending-generation')"
      class="generate-button-host"
    >
      <DsfrButton
        icon="ri-refresh-line"
        :disabled="true"
      >
        {{ $t('meeting-v2.deliverable-card.generate-button') }}
      </DsfrButton>
    </HoverTooltip>
    <DsfrButton
      v-else
      icon="ri-refresh-line"
      :disabled="generateDisabled"
      @click="generate"
    >
      {{ $t('meeting-v2.deliverable-card.generate-button') }}
    </DsfrButton>

    <hr class="w-full border-0 border-t border-t-[var(--grey-925-125)] m-0 pb-0.5" />

    <MeetingDeliverableList
      :transcription-item="transcriptionItem"
      :displayed-deliverables="displayedDeliverables"
      @download-transcription="onDownloadTranscription"
      @download-deliverable="onDownload"
    />
  </div>
</template>

<script setup lang="ts">
import MeetingDeliverableList from './MeetingDeliverableList.vue';
import CustomReportModal from './modals/CustomReportModal.vue';
import HoverTooltip from '@/components/core/HoverTooltip.vue';
import { useDeliverables } from '@/services/deliverables/use-deliverables';
import {
  mapDeliverableStatus,
  type DeliverableType,
} from '@/services/deliverables/deliverables.types';
import { getTranscriptionStatus } from '@/services/deliverables/deliverables.service';
import type { MeetingStatus } from '@/services/meetings/meetings.types';
import { useMeetings } from '@/services/meetings/use-meeting';
import { downloadFileFromAxios, extractFilenameFromResponse } from '@/utils/file';
import useToaster from '@/composables/use-toaster';
import { t } from '@/plugins/i18n';
import { useModal } from 'vue-final-modal';
import { useFeatureFlag } from '@/composables/use-feature-flag';

const props = defineProps<{ meetingId: number; meetingStatus: MeetingStatus }>();

const { getDeliverablesQuery, createDeliverableMutation, downloadDeliverableMutation } =
  useDeliverables();
const { downloadMutation } = useMeetings();

const { data: deliverables } = getDeliverablesQuery(props.meetingId);
const { mutate: createMutate, isPending: isCreating } = createDeliverableMutation(props.meetingId);
const { mutate: downloadMutate } = downloadDeliverableMutation();

const toaster = useToaster();

const isCustomReportEnabled = useFeatureFlag('custom_cr');
const selectedType = ref<DeliverableType | undefined>(undefined);
const customPrompt = ref('');

const activeDeliverables = computed(() =>
  (deliverables.value ?? []).filter(
    (d) =>
      d.type !== 'TRANSCRIPTION' && (d.type !== 'CUSTOM_REPORT' || isCustomReportEnabled.value),
  ),
);

const generatedTypes = computed(() => new Set(activeDeliverables.value.map((d) => d.type)));

const hasPendingDeliverable = computed(() =>
  activeDeliverables.value.some((d) => d.status === 'PENDING'),
);

const radioOptions = computed(() =>
  [
    {
      label: t('meeting-v2.deliverable-card.type.decision-record.label'),
      hint: t('meeting-v2.deliverable-card.type.decision-record.hint'),
      value: 'DECISION_RECORD' as DeliverableType,
      disabled: generatedTypes.value.has('DECISION_RECORD'),
    },
    {
      label: t('meeting-v2.deliverable-card.type.detailed-synthesis.label'),
      hint: t('meeting-v2.deliverable-card.type.detailed-synthesis.hint'),
      value: 'DETAILED_SYNTHESIS' as DeliverableType,
      disabled: generatedTypes.value.has('DETAILED_SYNTHESIS'),
    },
    {
      label: t('meeting-v2.deliverable-card.type.custom-report.label'),
      hint: t('meeting-v2.deliverable-card.type.custom-report.hint'),
      value: 'CUSTOM_REPORT' as DeliverableType,
      disabled: false,
    },
  ].filter((o) => o.value !== 'CUSTOM_REPORT' || isCustomReportEnabled.value),
);

const transcriptionStatus = computed(() => getTranscriptionStatus(props.meetingStatus));

const allGenerated = computed(() =>
  radioOptions.value.filter((o) => o.value !== 'CUSTOM_REPORT').every((o) => o.disabled),
);

const isTranscriptionInProgress = computed(
  () => transcriptionStatus.value !== null && transcriptionStatus.value !== 'AVAILABLE',
);

const generateDisabled = computed(
  () =>
    selectedType.value === undefined ||
    selectedType.value === 'CUSTOM_REPORT' ||
    allGenerated.value ||
    isCreating.value ||
    hasPendingDeliverable.value ||
    isTranscriptionInProgress.value,
);

const generateBlockedByPending = computed(() => hasPendingDeliverable.value);

const modalGenerateDisabled = computed(
  () => isCreating.value || hasPendingDeliverable.value || isTranscriptionInProgress.value,
);

const { open: openCustomReportModal } = useModal({
  component: CustomReportModal,
  attrs: {
    get initialPrompt() {
      return customPrompt.value;
    },
    get modalGenerateDisabled() {
      return modalGenerateDisabled.value;
    },
    onGenerate: (prompt: string) => {
      createMutate(
        { meeting_id: props.meetingId, type: 'CUSTOM_REPORT', custom_prompt: prompt },
        {
          onError: () => {
            toaster.addErrorMessage(t('error.deliverable-generation')!);
          },
        },
      );
      customPrompt.value = '';
      selectedType.value = undefined;
    },
    onUpdatePrompt: (value: string) => {
      customPrompt.value = value;
      selectedType.value = undefined;
    },
  },
});

function onSelectType(newType: string | number | boolean): void {
  if (newType === 'CUSTOM_REPORT') {
    openCustomReportModal();
  }
}

function generate(): void {
  if (selectedType.value === undefined || selectedType.value === 'CUSTOM_REPORT') return;
  createMutate(
    { meeting_id: props.meetingId, type: selectedType.value },
    {
      onError: () => {
        toaster.addErrorMessage(t('error.deliverable-generation')!);
      },
    },
  );
}

const TYPE_KEY_MAP: Record<string, string> = {
  DECISION_RECORD: 'decision-record',
  DETAILED_SYNTHESIS: 'detailed-synthesis',
  CUSTOM_REPORT: 'custom-report',
};

const displayedDeliverables = computed(() =>
  activeDeliverables.value.map((d) => ({
    id: d.id,
    title: t(`meeting-v2.deliverable-card.type.${TYPE_KEY_MAP[d.type]}.title`),
    status: mapDeliverableStatus(d.status as Exclude<typeof d.status, 'IN_PROGRESS'>),
    fileFormat: 'DOCX',
    fileSize: undefined,
  })),
);

function onDownload(deliverableId: number): void {
  downloadMutate(deliverableId, {
    onSuccess: (response) => {
      downloadFileFromAxios(response, extractFilenameFromResponse(response));
    },
    onError: () => {
      toaster.addErrorMessage(t('error.default')!);
    },
  });
}

const transcriptionItem = computed(() => {
  if (!transcriptionStatus.value) return null;
  return {
    title: t('meeting-v2.deliverable-card.type.transcription.title'),
    status: transcriptionStatus.value,
    fileFormat: 'DOCX',
  };
});

const { mutate: downloadTranscription } = downloadMutation();

function onDownloadTranscription(): void {
  downloadTranscription(props.meetingId, {
    onSuccess: (response) => {
      downloadFileFromAxios(response, extractFilenameFromResponse(response));
    },
    onError: () => {
      toaster.addErrorMessage(t('error.default')!);
    },
  });
}
</script>

<style scoped>
:deep(.fr-fieldset) {
  margin-bottom: 0;
}

.generate-button-host {
  position: relative;
  display: inline-flex;
  align-self: flex-start;
}
</style>
