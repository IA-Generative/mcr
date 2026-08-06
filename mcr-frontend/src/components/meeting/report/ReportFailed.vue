<template>
  <div class="mx-4 flex flex-col items-center gap-8">
    <div class="flex flex-col items-center gap-4">
      <img
        src="@dsfr-artwork/pictograms/system/warning.svg?url"
        role="presentation"
        class="h-22 w-22"
      />
      <div class="text-center">
        <h3 class="mb-6 text-xl font-bold text-blue-france-sun">
          {{ $t('meeting.transcription.transcription-failed.title') }}
        </h3>
        <p class="mb-4 text-lg text-grey-625">
          {{ $t('meeting.transcription.transcription-failed.description') }}
        </p>
      </div>
      <DsfrButton @click="$emit('onReset')">
        {{ $t('meeting.transcription.transcription-failed.button') }}
      </DsfrButton>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { DsfrButton } from '@gouvminint/vue-dsfr';

defineProps<{
  meetingId: number;
}>();
defineEmits<{ onReset: [] }>();
</script>
