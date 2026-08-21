<template>
  <section
    v-if="isOpen"
    class="fixed right-(--sticky-corner-margin) bottom-(--sticky-corner-margin) z-1000 w-(--import-sticky-width) rounded-lg bg-background-default-grey shadow-overlay"
    :aria-label="t('meeting.import.sticky.label')"
  >
    <header class="flex items-center justify-between gap-2 px-4 py-3">
      <p class="m-0 font-bold">{{ title }}</p>
      <DsfrButton
        :label="t('meeting.import.sticky.close')"
        icon="fr-icon-close-line"
        icon-only
        tertiary
        no-outline
        size="sm"
        @click="close"
      />
    </header>
    <p
      v-if="etaLabel"
      class="m-0 border-t border-border px-4 py-2 text-sm text-grey-mention"
      role="status"
    >
      {{ etaLabel }}
    </p>
    <ul class="m-0 max-h-[40vh] list-none overflow-y-auto p-0">
      <ImportStickyRow
        v-for="item in items"
        :key="item.id"
        :item="item"
        @retry="retryImport(item.id)"
      />
    </ul>
  </section>
</template>

<script setup lang="ts">
import ImportStickyRow from '@/components/import/ImportStickyRow.vue';
import { useImportMeeting } from '@/composables/use-import-meeting';
import { useImportStickyClose } from '@/composables/use-import-sticky-close';
import { useUploadBatch } from '@/composables/use-upload-batch';
import { t } from '@/plugins/i18n';
import { formatDurationLabel } from '@/utils/timeFormatting';

const { isOpen, items, batchTitle, batchEtaSeconds } = useUploadBatch();
const { close } = useImportStickyClose();
const { retryImport } = useImportMeeting();

const title = computed(() =>
  batchTitle.value ? t(batchTitle.value.key, batchTitle.value.params) : '',
);

const etaLabel = computed(() =>
  batchEtaSeconds.value === null
    ? ''
    : t('meeting.import.sticky.eta', {
        time: formatDurationLabel(Math.ceil(batchEtaSeconds.value)),
      }),
);
</script>
