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

    <DsfrButton
      icon="ri-refresh-line"
      :disabled="generateDisabled"
      @click="generate"
    >
      {{ $t('meeting-v2.deliverable-card.generate-button') }}
    </DsfrButton>

    <hr class="w-full border-0 border-t border-t-[var(--grey-925-125)] m-0 pb-0.5" />

    <MeetingDeliverableList
      :displayed-deliverables="displayedDeliverables"
      @download-deliverable="onDownload"
    />
  </div>
</template>

<script setup lang="ts">
import MeetingDeliverableList from './MeetingDeliverableList.vue';
import CustomReportModal from './modals/CustomReportModal.vue';
import { useDeliverables } from '@/services/deliverables/use-deliverables';
import {
  DeliverableType,
  mapDeliverableStatus,
  type DeliverableDto,
} from '@/services/deliverables/deliverables.types';
import { getTranscriptionStatus } from '@/services/deliverables/deliverables.service';
import type { MeetingStatus } from '@/services/meetings/meetings.types';
import { downloadFileFromAxios } from '@/utils/file';
import useToaster from '@/composables/use-toaster';
import { t } from '@/plugins/i18n';
import { useModal } from 'vue-final-modal';
import { useFeatureFlag } from '@/composables/use-feature-flag';

const props = defineProps<{ meetingId: number; meetingStatus: MeetingStatus }>();

const { getDeliverablesQuery, createDeliverableMutation, downloadDeliverableMutation } =
  useDeliverables();
const { data: deliverables } = getDeliverablesQuery(props.meetingId);
const { mutate: createMutate, isPending: isCreating } = createDeliverableMutation(props.meetingId);
const { mutate: downloadMutate } = downloadDeliverableMutation();

const toaster = useToaster();

const isCustomReportEnabled = useFeatureFlag('custom_cr');
const selectedType = ref<DeliverableType | undefined>(undefined);
const customPrompt = ref('');

const { open: openCustomReportModal } = useModal({
  component: CustomReportModal,
  attrs: {
    get initialPrompt() {
      return customPrompt.value;
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

const activeDeliverables = computed(() => {
  const DEFAULT_STATUS = 'PENDING';

  const PENDING_TRANSCRIPTION_DELIVERABLE = {
    type: 'TRANSCRIPTION',
    status: getTranscriptionStatus(props.meetingStatus) ?? DEFAULT_STATUS,
  } as DeliverableDto;

  if (deliverables.value && deliverables.value.length > 0) {
    return deliverables.value.filter(
      (d) => d.type !== 'CUSTOM_REPORT' || isCustomReportEnabled.value,
    );
  } else {
    return [PENDING_TRANSCRIPTION_DELIVERABLE];
  }
});

const generatedTypes = computed(() => new Set(activeDeliverables.value.map((d) => d.type)));

const hasPendingDeliverable = computed(() =>
  activeDeliverables.value.some((d) => d.status === 'PENDING' || d.status === 'IN_PROGRESS'),
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

const allGenerated = computed(() =>
  radioOptions.value.filter((o) => o.value !== 'CUSTOM_REPORT').every((o) => o.disabled),
);

const generateDisabled = computed(
  () =>
    selectedType.value === undefined ||
    selectedType.value === 'CUSTOM_REPORT' ||
    allGenerated.value ||
    isCreating.value ||
    hasPendingDeliverable.value,
);

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
  TRANSCRIPTION: 'transcription',
  DECISION_RECORD: 'decision-record',
  DETAILED_SYNTHESIS: 'detailed-synthesis',
  CUSTOM_REPORT: 'custom-report',
};

function mapDeliverableStatusOrDefaultToMeetingStatus(
  deliverable: DeliverableDto,
  meetingStatus: MeetingStatus,
) {
  if (deliverable.type == 'TRANSCRIPTION') {
    const DEFAULT_STATUS = 'PENDING';
    return getTranscriptionStatus(meetingStatus) ?? DEFAULT_STATUS;
  } else {
    return mapDeliverableStatus(
      deliverable.status as Exclude<typeof deliverable.status, 'IN_PROGRESS'>,
    );
  }
}

const displayedDeliverables = computed(() =>
  activeDeliverables.value.map((d) => ({
    id: d.id,
    title: t(`meeting-v2.deliverable-card.type.${TYPE_KEY_MAP[d.type]}.title`),
    status: mapDeliverableStatusOrDefaultToMeetingStatus(d, props.meetingStatus),
    fileFormat: 'DOCX',
    fileSize: undefined,
    externalUrl: d.external_url,
  })),
);

function onDownload(deliverableId: number): void {
  downloadMutate(deliverableId, {
    onSuccess: (response) => {
      downloadFileFromAxios(response, `livrable_${deliverableId}.docx`);
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
</style>
