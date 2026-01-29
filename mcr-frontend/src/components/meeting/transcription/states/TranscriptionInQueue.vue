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
        {{ $t('meeting.transcription.transcription-in-queue.title') }}
      </h3>
      <p class="text-lg text-[var(--default-text-grey)]">
        {{ $t('meeting.transcription.transcription-in-queue.description') }}
      </p>
    </div>

    <div
      v-if="!is_waiting_time_data_reached_deadline"
      class="fr-alert fr-alert--info fr-alert--sm pr-2"
    >
      <p>
        {{ $t('meeting.transcription.transcription-in-queue.estimation') }}
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
          {{ $t('meeting.transcription.transcription-in-queue.reachement-deadline') }}
        </span>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useQuery } from '@tanstack/vue-query';
import { getTranscriptionWaitingTime } from '@/services/meetings/meetings.service';
import { TRANSCRIPTION_WAITING_TIME_POLLING_INTERVAL } from '@/config/meeting';
import { formatRoundedDurationMinutes } from '@/utils/timeFormatting';

const is_waiting_time_data_reached_deadline = computed(() => {
  return waiting_time_data.value && waiting_time_data.value.estimation_duration_minutes <= 0;
});

const props = defineProps<{
  meetingId: number;
  meetingName?: string;
}>();

// Récupération du temps d'attente estimé depuis l'API
const { data: waiting_time_data } = useQuery({
  queryKey: ['transcription-waiting-time', props.meetingId],
  queryFn: () => getTranscriptionWaitingTime(props.meetingId),
  refetchInterval: TRANSCRIPTION_WAITING_TIME_POLLING_INTERVAL,
});
</script>
