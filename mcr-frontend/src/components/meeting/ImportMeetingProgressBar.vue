<template>
  <div class="flex flex-col items-center gap-4 py-6">
    <ProgressBar :progress="progress" />
    <div class="flex w-fit gap-4 items-center">
      <p>
        <span class="font-semibold">{{
          isProgressComplete(progress)
            ? $t('meeting.import-form.fields.file.download-done')
            : $t('meeting.import-form.fields.file.download-in-progress')
        }}</span>
        &nbsp;
        <span>{{ `(${progress}%)` }}</span>
      </p>
      <DsfrButton
        class="ml-auto"
        tertiary
        no-outline
        type="button"
        @click="$emit('onCancel')"
        >{{ $t('common.cancel') }}</DsfrButton
      >
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  progress: number;
}>();

defineEmits<{
  onCancel: [];
}>();

function isProgressComplete(progress: number): boolean {
  return progress >= 100;
}
</script>
