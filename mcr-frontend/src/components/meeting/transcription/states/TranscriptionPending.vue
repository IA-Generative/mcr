<template>
  <div class="flex flex-col items-center gap-6">
    <!-- Icon Texte -->
    <div class="flex justify-center items-center w-20 h-20">
      <img
        src="@dsfr-artwork/pictograms/document/document.svg?url"
        role="presentation"
        class="w-22 h-22"
      />
    </div>

    <!-- Titre et sous-titre -->
    <div class="text-center max-w-2xl">
      <h3 class="text-xl font-bold mb-4 text-[var(--blue-france-sun-113-625)]">
        {{ $t('meeting.transcription.transcription-pending.title') }}
      </h3>
      <p class="text-lg text-[var(--default-text-grey)]">
        {{ $t('meeting.transcription.transcription-pending.description') }}
      </p>
    </div>

    <div
      v-if="!is_waiting_time_data_reached_deadline"
      class="fr-alert fr-alert--info fr-alert--sm pr-2"
    >
      <p>
        {{ $t('meeting.transcription.transcription-pending.estimation') }}
        <span class="font-bold">
          {{ formatRoundedDurationMinutes(waiting_time_data?.estimation_duration_minutes) }}
        </span>
      </p>
    </div>
    <div
      v-else
      class="fr-alert fr-alert--warning fr-alert--sm pr-2"
    >
      <p>
        <span class="font-bold">
          {{ $t('meeting.transcription.transcription-pending.reachement-deadline') }}
        </span>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { formatRoundedDurationMinutes } from '@/utils/timeFormatting';
import { useMeetings } from '@/services/meetings/use-meeting';

const props = defineProps<{
  meetingId: number;
}>();

const { getMeetingTranscriptionWaitTime } = useMeetings();
const { data: waiting_time_data } = getMeetingTranscriptionWaitTime(props.meetingId);

const is_waiting_time_data_reached_deadline = computed(() => {
  return waiting_time_data.value && waiting_time_data.value.estimation_duration_minutes <= 0;
});
</script>
