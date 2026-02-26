<template>
  <div class="flex flex-col justify-center items-center py-28">
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
defineEmits<{ onGenerate: [] }>();
</script>
