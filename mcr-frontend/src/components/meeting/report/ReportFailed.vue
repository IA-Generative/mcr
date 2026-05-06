<template>
  <div class="flex flex-col items-center gap-8 mx-4">
    <div class="flex flex-col items-center gap-4">
      <img
        src="@dsfr-artwork/pictograms/system/warning.svg?url"
        role="presentation"
        class="w-22 h-22"
      />
      <div class="text-center">
        <h3 class="text-xl font-bold mb-6 text-blue-france-sun">
          {{ $t('meeting.transcription.transcription-failed.title') }}
        </h3>
        <p class="text-lg mb-4 text-grey-625">
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
