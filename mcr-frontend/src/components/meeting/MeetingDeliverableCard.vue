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

    <MeetingDeliverableList :active-deliverables="activeDeliverables" />
  </div>
</template>

<script setup lang="ts">
import MeetingDeliverableList from './MeetingDeliverableList.vue';
import CustomReportModal from './modals/CustomReportModal.vue';
import { useDeliverables } from '@/services/deliverables/use-deliverables';
import { DeliverableType, type DeliverableDto } from '@/services/deliverables/deliverables.types';
import { getTranscriptionStatus } from '@/services/deliverables/deliverables.service';
import type { MeetingStatus } from '@/services/meetings/meetings.types';
import useToaster from '@/composables/use-toaster';
import { t } from '@/plugins/i18n';
import { useModal } from 'vue-final-modal';
import { useFeatureFlag } from '@/composables/use-feature-flag';

const props = defineProps<{ meetingId: number; meetingStatus: MeetingStatus }>();

const { getDeliverablesQuery, createDeliverableMutation } = useDeliverables();
const { data: deliverables } = getDeliverablesQuery(props.meetingId);
const { mutate: createMutate, isPending: isCreating } = createDeliverableMutation(props.meetingId);

const toaster = useToaster();

const isCustomReportEnabled = useFeatureFlag('custom_cr');
const selectedType = ref<DeliverableType | undefined>(undefined);
const customPrompt = ref('');

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

const successfullyGeneratedTypes = computed(
  () => new Set(activeDeliverables.value.map((d) => d.type)),
);

const hasPendingDeliverable = computed(() =>
  activeDeliverables.value.some((d) => d.status === 'PENDING' || d.status === 'IN_PROGRESS'),
);

const radioOptions = computed(() => [
  {
    label: t('meeting-v2.deliverable-card.type.decision-record.label'),
    hint: t('meeting-v2.deliverable-card.type.decision-record.hint'),
    value: 'DECISION_RECORD',
    disabled: successfullyGeneratedTypes.value.has('DECISION_RECORD'),
  },
  {
    label: t('meeting-v2.deliverable-card.type.detailed-synthesis.label'),
    hint: t('meeting-v2.deliverable-card.type.detailed-synthesis.hint'),
    value: 'DETAILED_SYNTHESIS',
    disabled: successfullyGeneratedTypes.value.has('DETAILED_SYNTHESIS'),
  },
  {
    label: t('meeting-v2.deliverable-card.type.structured-minutes.label'),
    hint: t('meeting-v2.deliverable-card.type.structured-minutes.hint'),
    value: 'STRUCTURED_MINUTES' as DeliverableType,
    disabled: successfullyGeneratedTypes.value.has('STRUCTURED_MINUTES'),
  },
  {
    label: t('meeting-v2.deliverable-card.type.custom-report.label'),
    hint: t('meeting-v2.deliverable-card.type.custom-report.hint'),
    value: 'CUSTOM_REPORT',
    disabled: false,
  },
]);

const generateDisabled = computed(
  () =>
    selectedType.value === undefined ||
    selectedType.value === 'CUSTOM_REPORT' ||
    isCreating.value ||
    hasPendingDeliverable.value,
);

const modalGenerateDisabled = computed(() => isCreating.value || hasPendingDeliverable.value);

const { open: openCustomReportModal } = useModal({
  component: CustomReportModal,
  attrs: {
    get initialPrompt() {
      return customPrompt.value;
    },
    get generateBlockedByPending() {
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
</script>

<style scoped>
:deep(.fr-fieldset) {
  margin-bottom: 0;
}
</style>
