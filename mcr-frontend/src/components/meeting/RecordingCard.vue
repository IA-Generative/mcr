<template>
  <div class="flex flex-col items-center gap-5">
    <h2 class="font-bold text-3xl/10 text-blue-france-sun">
      {{ $t('meeting-v2.visio-recording.title') }}
    </h2>

    <LiveRecordingInProgress
      v-if="isRecordLocally"
      :meeting-id="meetingId"
    />

    <VisioRecordingCard
      v-else-if="isOnlineMeeting({ name_platform: props.namePlatform })"
      :meeting-id="meetingId"
      :status="status"
      :start-date="startDate"
    />

    <a
      v-if="isRecordLocally"
      href=""
      class="fr-link fr-link--sm fr-link--icon-left fr-icon-question-line self-end mr-4"
      @click.prevent="openLiveAdvices"
    >
      {{ $t('meeting-v2.recording.advices.title') }}
    </a>
  </div>
</template>

<script setup lang="ts">
import { useModal } from 'vue-final-modal';
import LiveRecordingInProgress from '@/components/meeting/LiveRecordingInProgress.vue';
import VisioRecordingCard from '@/components/meeting/VisioRecordingCard.vue';
import LiveMeetingAdvicesModal from '@/components/meeting/modals/LiveMeetingAdvicesModal.vue';
import type { MeetingStatus, AllMeetingPlatforms } from '@/services/meetings/meetings.types';
import { isOnlineMeeting } from '@/services/meetings/meetings.types';

const props = defineProps<{
  meetingId: number;
  status: MeetingStatus;
  namePlatform: AllMeetingPlatforms;
  startDate?: string;
}>();

const isRecordLocally = computed(() => props.namePlatform === 'MCR_RECORD');

const { open: openLiveAdvices } = useModal({ component: LiveMeetingAdvicesModal });
</script>
