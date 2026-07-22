<template>
  <div class="bg-white p-6 flex flex-col gap-4 border border-[var(--grey-975-75-hover)]">
    <h2 class="text-blue-france-sun font-bold text-2xl">
      {{ $t('meeting-v2.deliverable-card.title') }}
    </h2>
    <p class="text-[var(--text-default-grey)] m-0">
      {{ $t('meeting-v2.deliverable-card.description') }}
    </p>

    <div class="grid grid-cols-2 max-sm:grid-cols-1 gap-4 items-stretch">
      <DeliverableTypeCard
        v-for="type in types"
        :key="type"
        :type="type"
        :deliverable="findActive(type)"
        :is-generating="pendingTypes.includes(type)"
        :transcription-ready="transcriptionReady"
        :transcription-failed="transcriptionFailed"
        @generate="() => onGenerate(type)"
        @customize="openCustomReportModal"
        @download="onDownload"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import DeliverableTypeCard from './DeliverableTypeCard.vue';
import CustomReportModal from './modals/CustomReportModal.vue';
import { useDeliverables } from '@/services/deliverables/use-deliverables';
import type { DeliverableType } from '@/services/deliverables/deliverables.types';
import useToaster from '@/composables/use-toaster';
import { t } from '@/plugins/i18n';
import { useModal } from 'vue-final-modal';
import { useFeatureFlag } from '@/composables/use-feature-flag';
import { downloadFileFromAxios, extractFilenameFromResponse } from '@/utils/file';

const props = defineProps<{ meetingId: number }>();

const { getDeliverablesQuery, createDeliverableMutation, downloadDeliverableMutation } =
  useDeliverables();
const { data: deliverables } = getDeliverablesQuery(props.meetingId);
const { mutate: createMutate } = createDeliverableMutation(props.meetingId);
const { mutate: downloadMutate } = downloadDeliverableMutation();

const toaster = useToaster();
const isCustomReportEnabled = useFeatureFlag('custom_cr');

const customPrompt = ref('');
const pending = ref<Partial<Record<DeliverableType, number | null>>>({});

const pendingTypes = computed(() => Object.keys(pending.value) as DeliverableType[]);

function clearPending(type: DeliverableType): void {
  const next = { ...pending.value };
  delete next[type];
  pending.value = next;
}

const types = computed<DeliverableType[]>(() => {
  const base: DeliverableType[] = ['TRANSCRIPTION', 'DECISION_RECORD', 'DETAILED_SYNTHESIS'];
  return isCustomReportEnabled.value ? [...base, 'CUSTOM_REPORT'] : base;
});

const transcriptionReady = computed(
  () =>
    deliverables.value?.some((d) => d.type === 'TRANSCRIPTION' && d.status === 'AVAILABLE') ??
    false,
);

const transcriptionFailed = computed(
  () =>
    deliverables.value?.some((d) => d.type === 'TRANSCRIPTION' && d.status === 'FAILED') ?? false,
);

function findActive(type: DeliverableType) {
  return deliverables.value?.find((d) => d.type === type);
}

watch(deliverables, () => {
  for (const type of pendingTypes.value) {
    const currentId = findActive(type)?.id ?? null;
    if (currentId !== pending.value[type]) clearPending(type);
  }
});

function requestGeneration(type: DeliverableType, prompt?: string): void {
  pending.value = { ...pending.value, [type]: findActive(type)?.id ?? null };
  createMutate(
    { meeting_id: props.meetingId, type, custom_prompt: prompt },
    {
      onError: () => {
        clearPending(type);
        toaster.addErrorMessage(t('error.deliverable-generation')!);
      },
    },
  );
}

function onGenerate(type: DeliverableType): void {
  requestGeneration(type);
}

const { open: openCustomReportModal } = useModal({
  component: CustomReportModal,
  attrs: {
    get initialPrompt() {
      return customPrompt.value;
    },
    generateBlockedByPending: false,
    onGenerate: (prompt: string) => {
      requestGeneration('CUSTOM_REPORT', prompt);
      customPrompt.value = '';
    },
    onUpdatePrompt: (value: string) => {
      customPrompt.value = value;
    },
  },
});

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
</script>
