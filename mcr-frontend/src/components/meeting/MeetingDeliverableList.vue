<template>
  <div
    v-if="displayedDeliverables.length"
    class="flex gap-2 flex-wrap"
  >
    <DeliverableItem
      v-for="item in displayedDeliverables"
      :key="item.id"
      :title="item.title"
      :status="item.status"
      :external-url="item.externalUrl"
      @download="() => onDownload(item.id)"
    />
  </div>
</template>

<script setup lang="ts">
import { useDeliverables } from '@/services/deliverables/use-deliverables.ts';
import DeliverableItem from './DeliverableItem.vue';
import type { DeliverableDto } from '@/services/deliverables/deliverables.types';
import { downloadFileFromAxios, extractFilenameFromResponse } from '@/utils/file.ts';
import useToaster from '@/composables/use-toaster.ts';
import { t } from '@/plugins/i18n.ts';

const props = defineProps<{
  activeDeliverables: DeliverableDto[];
}>();

const toaster = useToaster();

const { downloadDeliverableMutation } = useDeliverables();
const { mutate: downloadMutate } = downloadDeliverableMutation();

const TYPE_KEY_MAP: Record<string, string> = {
  TRANSCRIPTION: 'transcription',
  DECISION_RECORD: 'decision-record',
  DETAILED_SYNTHESIS: 'detailed-synthesis',
  STRUCTURED_MINUTES: 'structured-minutes',
  CUSTOM_REPORT: 'custom-report',
};

const displayedDeliverables = computed(() =>
  props.activeDeliverables.map((d) => ({
    id: d.id,
    title: t(`meeting-v2.deliverable-card.type.${TYPE_KEY_MAP[d.type]}.title`),
    status: d.status,
    externalUrl: d.external_url,
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
</script>
