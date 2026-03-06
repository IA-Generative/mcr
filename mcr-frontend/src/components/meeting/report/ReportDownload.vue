<template>
  <div class="flex justify-center items-center py-28 gap-4">
    <DsfrButton
      type="button"
      secondary
      icon="fr-icon-refresh-line"
      @click="$emit('onReset')"
    >
      {{ $t('meeting.report.reset') }}
    </DsfrButton>
    <DsfrButton
      type="button"
      icon="fr-icon-download-fill"
      @click="$emit('onGenerate')"
    >
      {{ $t('meeting.report.download') }}
    </DsfrButton>
  </div>
</template>

<script setup lang="ts">
defineEmits<{ onGenerate: []; onReset: [] }>();
</script>
