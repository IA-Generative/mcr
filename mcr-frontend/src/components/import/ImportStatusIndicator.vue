<template>
  <ImportProgressRing
    v-if="ring"
    class="shrink-0"
    :ratio="ring.ratio"
    :complete="ring.complete"
    :label="ring.label"
  />
  <span
    v-else
    role="img"
    class="inline-flex shrink-0"
    :class="glyph.class"
    :aria-label="glyph.label"
  >
    <VIcon
      :name="glyph.icon"
      :animation="glyph.animation"
    />
  </span>
</template>

<script setup lang="ts">
import ImportProgressRing from '@/components/import/ImportProgressRing.vue';
import { useUploadBatch, type UploadItem } from '@/composables/use-upload-batch';
import { t } from '@/plugins/i18n';

const STATUS_I18N = 'meeting.import.sticky.status';

const props = defineProps<{ item: UploadItem }>();

const { getProgressRatio } = useUploadBatch();

const ring = computed(() => {
  const { status } = props.item;
  if (status !== 'uploading' && status !== 'done') {
    return null;
  }
  return {
    ratio: getProgressRatio(props.item),
    complete: status === 'done',
    label: t(`${STATUS_I18N}.${status}`),
  };
});

const glyph = computed(() => {
  switch (props.item.status) {
    case 'transcoding':
      return {
        class: 'text-blue-france-sun',
        label: t(`${STATUS_I18N}.transcoding`),
        icon: 'ri-loader-3-line',
        animation: 'spin' as const,
      };
    case 'error':
      return {
        class: 'text-error-425',
        label: t(`${STATUS_I18N}.error`),
        icon: 'ri-error-warning-fill',
      };
    default:
      return {
        class: 'text-grey-mention',
        label: t(`${STATUS_I18N}.pending`),
        icon: 'ri-pause-circle-line',
      };
  }
});
</script>
