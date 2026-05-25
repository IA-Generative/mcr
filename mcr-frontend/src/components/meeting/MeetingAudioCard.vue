<template>
  <div
    v-if="isAudioAvailable"
    class="audio-card"
  >
    <h2 class="audio-card__title">{{ $t('meeting-v2.audio-card.title') }}</h2>
    <p class="audio-card__info">
      <VIcon
        name="ri-time-line"
        scale="0.9"
      />
      <i18n-t
        keypath="meeting-v2.audio-card.availability"
        tag="span"
      >
        <template #nbDays>
          <span style="font-weight: bold">
            {{ MAX_DELAY_TO_FETCH_AUDIO }}
            {{ $t('meetings_v2.availability-alert-description.days') }}
          </span>
        </template>
      </i18n-t>
    </p>

    <DsfrButton
      v-if="!isMeetingAudioRequested"
      secondary
      icon="fr-icon-headphone-line"
      @click="requestAudio"
    >
      {{ $t('meeting-v2.audio-card.button') }}
    </DsfrButton>

    <VIcon
      v-else-if="isLoadingAudio"
      name="ri-loader-3-line"
      animation="spin"
    />

    <DsfrNotice
      v-else-if="audioError"
      :title="$t('meeting-v2.audio-card.error')"
      type="alert"
    />

    <audio
      v-else-if="audioSrc"
      ref="audioEl"
      controls
      controlslist="nodownload"
      :src="audioSrc"
      :aria-label="$t('meeting-v2.audio-card.player-label')"
      class="w-full"
      @loadedmetadata="recoverAudioDuration"
      @timeupdate="onDurationRecovered"
    ></audio>
  </div>
</template>

<script setup lang="ts">
import HttpService, { API_PATHS } from '@/services/http/http.service';
import { MAX_DELAY_TO_FETCH_AUDIO } from '@/config/meeting';
import { differenceInDays, parseISO } from 'date-fns';
import type { MeetingStatus } from '@/services/meetings/meetings.types';

const AUDIO_ELIGIBLE_STATUSES: MeetingStatus[] = [
  'CAPTURE_DONE',
  'TRANSCRIPTION_PENDING',
  'TRANSCRIPTION_IN_PROGRESS',
  'TRANSCRIPTION_DONE',
  'TRANSCRIPTION_FAILED',
  'REPORT_PENDING',
  'REPORT_FAILED',
  'REPORT_DONE',
];

const props = defineProps<{
  meetingId: number;
  creationDate: string;
  status: MeetingStatus;
}>();

const isMeetingRecent = computed(
  () => differenceInDays(new Date(), parseISO(props.creationDate)) <= MAX_DELAY_TO_FETCH_AUDIO,
);

const isAudioAvailable = computed(
  () => isMeetingRecent.value && AUDIO_ELIGIBLE_STATUSES.includes(props.status),
);

const audioStorageKey = `mcr-audio-required-${props.meetingId}`;
const isMeetingAudioRequested = ref(localStorage.getItem(audioStorageKey) === 'true');

const audioSrc = ref<string>();
const isLoadingAudio = ref(true);
const audioError = ref(false);

const audioEl = useTemplateRef<HTMLAudioElement>('audioEl');
const isRecoveringDuration = ref(false);
const DURATION_RECOVERY_TIMEOUT_MS = 1000;

function requestAudio(): void {
  isMeetingAudioRequested.value = true;
  localStorage.setItem(audioStorageKey, 'true');
}

function recoverAudioDuration(): void {
  const el = audioEl.value;
  if (!el || el.duration !== Infinity) return;
  isRecoveringDuration.value = true;
  el.currentTime = Number.MAX_SAFE_INTEGER;
  setTimeout(onDurationRecovered, DURATION_RECOVERY_TIMEOUT_MS);
}

function onDurationRecovered(): void {
  if (!isRecoveringDuration.value) return;
  const el = audioEl.value;
  if (!el) return;
  isRecoveringDuration.value = false;
  el.currentTime = 0;
}

watch(
  isMeetingAudioRequested,
  async (isRequired) => {
    if (!isRequired) return;
    try {
      const response = await HttpService.get(`${API_PATHS.MEETINGS}/${props.meetingId}/audio`, {
        responseType: 'blob',
      });
      audioSrc.value = URL.createObjectURL(response.data);
    } catch (err) {
      console.error('Failed to fetch audio', err);
      audioError.value = true;
    } finally {
      isLoadingAudio.value = false;
    }
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  if (audioSrc.value) {
    URL.revokeObjectURL(audioSrc.value);
  }
});
</script>

<style scoped>
.audio-card {
  background-color: white;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  border-width: 1px;
  border-color: var(--grey-975-75-hover);
}

.audio-card__title {
  color: var(--blue-france-sun-113-625);
  font-weight: bold;
  font-size: 1.5rem;
}

.audio-card__info {
  color: var(--text-default-grey);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
</style>
