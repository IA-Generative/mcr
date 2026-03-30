<template>
  <div class="flex justify-center items-start py-28 gap-4">
    <DsfrButton
      type="button"
      secondary
      icon="fr-icon-refresh-line"
      @click="$emit('onReset')"
    >
      {{ $t('meeting.report.reset') }}
    </DsfrButton>

    <div
      v-if="reportDriveUrl"
      class="flex flex-col items-center gap-2"
    >
      <a
        :href="reportDriveUrl"
        target="_blank"
        rel="noopener noreferrer"
        class="fr-btn fr-btn--icon-right fr-icon-external-link-line"
      >
        {{ $t('meeting.report.open-on-drive') }}
      </a>
      <a
        href="#"
        class="fr-link fr-link--sm"
        @click.prevent="$emit('onGenerate')"
      >
        {{ $t('meeting.report.download') }}
      </a>
    </div>

    <DsfrButton
      v-else
      type="button"
      icon="fr-icon-download-fill"
      @click="$emit('onGenerate')"
    >
      {{ $t('meeting.report.download') }}
    </DsfrButton>
  </div>
</template>

<script setup lang="ts">
import type { DeliverableDto } from '@/services/meetings/meetings.types';

const props = withDefaults(
  defineProps<{
    deliverables?: DeliverableDto[];
  }>(),
  { deliverables: () => [] },
);
defineEmits<{ onGenerate: []; onReset: [] }>();

const reportDriveUrl = computed(() => {
  const deliverable = props.deliverables.find((d) => d.file_type === 'REPORT' && d.external_url);
  return deliverable?.external_url ?? null;
});
</script>
