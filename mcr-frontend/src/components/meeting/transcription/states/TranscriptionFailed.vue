<template>
  <div class="flex flex-col items-center gap-8 mx-4">
    <div class="flex flex-col items-center gap-4">
      <img
        src="@dsfr-artwork/pictograms/system/warning.svg?url"
        role="presentation"
        class="w-22 h-22"
      />
      <div class="text-center">
        <h3 class="text-xl font-bold mb-6 text-[var(--blue-france-sun-113-625)]">
          {{ $t('meeting.transcription.transcription-failed.title') }}
        </h3>
        <p class="text-lg mb-4 text-[var(--default-text-grey)]">
          {{ $t('meeting.transcription.transcription-failed.description') }}
        </p>
      </div>
      <DsfrButton
        :disabled="isTranscriptionStartPending"
        @click="() => restartTranscription(meetingId)"
      >
        <span
          aria-hidden="true"
          class="fr-icon-refresh-line"
        ></span>
        {{ $t('meeting.transcription.transcription-failed.button') }}
        <VIcon
          v-if="isTranscriptionStartPending"
          name="ri-loader-3-line"
          animation="spin"
          class="ml-2"
        />
      </DsfrButton>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { useMeetings } from '@/services/meetings/use-meeting';
import { DsfrButton } from '@gouvminint/vue-dsfr';

defineProps<{
  meetingId: number;
}>();

const { startTranscriptionMutation } = useMeetings();
const { mutate: restartTranscription, isPending: isTranscriptionStartPending } =
  startTranscriptionMutation();
</script>
