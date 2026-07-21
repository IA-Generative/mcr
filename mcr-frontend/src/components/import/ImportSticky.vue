<template>
  <section
    v-if="isOpen"
    class="import-sticky"
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
      class="m-0 border-t border-default-grey px-4 py-2 text-sm text-grey-mention"
      role="status"
    >
      {{ etaLabel }}
    </p>
    <ul class="m-0 list-none overflow-y-auto p-0 max-h-[40vh]">
      <ImportStickyRow
        v-for="item in items"
        :key="item.id"
        :item="item"
      />
    </ul>
  </section>
</template>

<script setup lang="ts">
import ImportStickyRow from '@/components/import/ImportStickyRow.vue';
import { useImportStickyClose } from '@/composables/use-import-sticky-close';
import { useUploadBatch } from '@/composables/use-upload-batch';
import { t } from '@/plugins/i18n';
import { formatDurationLabel } from '@/utils/timeFormatting';

const { isOpen, items, batchTitle, batchEtaSeconds } = useUploadBatch();
const { close } = useImportStickyClose();

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

<style scoped>
.import-sticky {
  position: fixed;
  z-index: 1000;
  bottom: var(--sticky-corner-margin);
  right: var(--sticky-corner-margin);
  width: var(--import-sticky-width);
  background-color: var(--background-default-grey, #fff);
  border-radius: 8px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.16);
}
</style>
