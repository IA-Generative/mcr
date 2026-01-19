<template>
  <div class="flex flex-col items-center gap-5">
    <div class="flex justify-center items-center w-20 h-20 m-8">
      <img
        src="@dsfr-artwork/pictograms/system/warning.svg?url"
        role="presentation"
        class="w-17 h-17"
      />
    </div>

    <div class="text-center">
      <h3 class="text-lg font-semibold mb-2 text-blue-900">
        {{ $t('meeting.transcription.bot-connection-failed.title') }}
      </h3>
      <p class="text-gray-600 mb-4">
        {{ $t('meeting.transcription.bot-connection-failed.description') }}
      </p>

      <DsfrButton
        :disabled="isPending"
        @click="retryConnection"
      >
        <span
          aria-hidden="true"
          class="fr-icon-refresh-line"
        ></span>
        {{ $t('meeting.transcription.bot-connection-failed.retry-button') }}
        <VIcon
          v-if="isPending"
          name="ri-loader-3-line"
          animation="spin"
          class="ml-2"
        />
      </DsfrButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useMeetings } from '@/services/meetings/use-meeting';

const props = defineProps<{
  meetingId: number;
  meetingName?: string;
}>();

const { startCaptureMutation } = useMeetings();
const { mutate: startCapture, isPending } = startCaptureMutation();

function retryConnection() {
  // Relancer la capture pour remettre le meeting en CAPTURE_PENDING
  startCapture(props.meetingId);
}
</script>
