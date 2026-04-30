<template>
  <div class="deliverable-card">
    <h2 class="deliverable-card__title">{{ $t('meeting-v2.deliverable-card.title') }}</h2>
    <p class="deliverable-card__description">{{ $t('meeting-v2.deliverable-card.description') }}</p>

    <DsfrRadioButtonSet
      v-model="selectedType"
      name="deliverable-type"
      :options="radioOptions"
    />

    <DsfrButton
      icon="ri-refresh-line"
      :disabled="generateDisabled"
      @click="generate"
    >
      {{ $t('meeting-v2.deliverable-card.generate-button') }}
    </DsfrButton>

    <hr class="deliverable-card__separator" />

    <div
      v-if="transcriptionItem || displayedDeliverables.length"
      class="deliverable-card__items"
    >
      <DeliverableItem
        v-if="transcriptionItem"
        class="border border-[#DDDDDD]"
        :deliverable-id="TRANSCRIPTION_ITEM_ID"
        :title="transcriptionItem.title"
        :status="transcriptionItem.status"
        :file-format="transcriptionItem.fileFormat"
        @download="onDownloadTranscription"
      />
      <DeliverableItem
        v-for="item in displayedDeliverables"
        :key="item.id"
        :deliverable-id="item.id"
        :title="item.title"
        :status="item.status"
        :file-format="item.fileFormat"
        :file-size="item.fileSize"
        @download="onDownload"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import DeliverableItem from './DeliverableItem.vue';
import { useDeliverables } from '@/services/deliverables/use-deliverables';
import {
  mapDeliverableStatus,
  type DeliverableType,
} from '@/services/deliverables/deliverables.types';
import { getTranscriptionStatus } from '@/services/deliverables/deliverables.service';
import type { MeetingStatus } from '@/services/meetings/meetings.types';
import { useMeetings } from '@/services/meetings/use-meeting';
import { downloadFileFromAxios } from '@/utils/file';
import useToaster from '@/composables/use-toaster';
import { t } from '@/plugins/i18n';

const TRANSCRIPTION_ITEM_ID = -1;

const props = defineProps<{ meetingId: number; meetingStatus: MeetingStatus }>();

const { getDeliverablesQuery, createDeliverableMutation, downloadDeliverableMutation } =
  useDeliverables();
const { downloadMutation } = useMeetings();

const { data: deliverables } = getDeliverablesQuery(props.meetingId);
const { mutate: createMutate, isPending: isCreating } = createDeliverableMutation(props.meetingId);
const { mutate: downloadMutate } = downloadDeliverableMutation();

const toaster = useToaster();

const selectedType = ref<DeliverableType>('DECISION_RECORD');

const activeDeliverables = computed(() => deliverables.value ?? []);

const generatedTypes = computed(() => new Set(activeDeliverables.value.map((d) => d.type)));

const hasPendingDeliverable = computed(() =>
  activeDeliverables.value.some((d) => d.status === 'PENDING'),
);

const radioOptions = computed(() => [
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
]);

const transcriptionStatus = computed(() => getTranscriptionStatus(props.meetingStatus));

const allGenerated = computed(() => radioOptions.value.every((o) => o.disabled));

const isTranscriptionInProgress = computed(
  () => transcriptionStatus.value !== null && transcriptionStatus.value !== 'AVAILABLE',
);

const generateDisabled = computed(
  () =>
    allGenerated.value ||
    isCreating.value ||
    hasPendingDeliverable.value ||
    isTranscriptionInProgress.value,
);

function generate(): void {
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
      downloadFileFromAxios(response, `livrable_${deliverableId}.docx`);
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
      downloadFileFromAxios(response, `transcription_${props.meetingId}.docx`);
    },
    onError: () => {
      toaster.addErrorMessage(t('error.default')!);
    },
  });
}
</script>

<style scoped>
.deliverable-card {
  background-color: white;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  border-width: 1px;
  border-color: var(--grey-975-75-hover);
}

.deliverable-card__title {
  color: var(--blue-france-sun-113-625);
  font-weight: bold;
  font-size: 1.5rem;
}

.deliverable-card__description {
  color: var(--text-default-grey);
  margin: 0;
}

.deliverable-card__separator {
  width: 100%;
  border: none;
  border-top: 1px var(--grey-925-125);
  margin: 0;
  padding-bottom: 2px;
}

.deliverable-card__items {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

:deep(.fr-fieldset) {
  margin-bottom: 0;
}
</style>
