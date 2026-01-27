<template>
  <div class="flex flex-col items-center gap-6">
    <!-- Icon Crayon -->
    <div class="flex justify-center items-center w-20 h-20">
      <img
        src="@dsfr-artwork/pictograms/document/conclusion.svg?url"
        role="presentation"
        class="w-22 h-22"
      />
    </div>

    <!-- Titre et sous-titre -->
    <div class="text-center max-w-2xl">
      <h3 class="text-xl font-bold mb-4 text-[var(--blue-france-sun-113-625)]">
        {{ $t('meeting.transcription.transcription-in-progress.title') }}
      </h3>
      <p class="text-lg text-[var(--default-text-grey)]">
        {{ $t('meeting.transcription.transcription-in-progress.description') }}
      </p>
    </div>

    <TranscriptionWaitTime
      :message="$t('meeting.transcription.transcription-in-progress.wait-message')"
      :waiting-time-minutes="waiting_time_data?.estimation_duration_minutes"
    />
  </div>
</template>

<script setup lang="ts">
import { useMeetings } from '@/services/meetings/use-meeting';

const props = defineProps<{
  meetingId: number;
}>();

const { getMeetingTranscriptionWaitTime } = useMeetings();
const { data: waiting_time_data } = getMeetingTranscriptionWaitTime(props.meetingId);
</script>
