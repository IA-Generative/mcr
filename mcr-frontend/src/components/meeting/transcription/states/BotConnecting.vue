<template>
  <div class="flex flex-col items-center">
    <div class="flex justify-center items-center w-20 h-20 m-6">
      <img
        src="@dsfr-artwork/pictograms/system/information.svg?url"
        role="presentation"
        class="w-22 h-22"
      />
    </div>

    <div class="text-center">
      <h3 class="text-xl font-semibold mb-6 text-blue-france-sun">
        {{ $t('meeting.transcription.bot-connecting.title') }}
      </h3>
      <h4 class="text-lg font-semibold mb-4 text-grey-625">
        {{ $t('meeting.transcription.bot-connecting.subtitle') }}
      </h4>
      <p class="text-grey-625">
        {{ $t('meeting.transcription.bot-connecting.description') }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  meetingId: number;
  meetingName?: string;
}>();
</script>
