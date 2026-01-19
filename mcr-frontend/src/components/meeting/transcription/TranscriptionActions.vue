<template>
  <component
    :is="currentStateComponent"
    :meeting-id="meeting.id"
    :meeting-name="meeting.name"
    :meeting-status="meeting.status"
  />
</template>

<script setup lang="ts">
import { type MeetingDto, type MeetingStatus } from '@/services/meetings/meetings.types';

import NoneStateComponent from './states/TranscriptionNone.vue';
import RecordingInProgressStateComponent from './states/RecordingInProgress.vue';
import InProgressStateComponent from './states/TranscriptionInProgress.vue';
import DoneStateComponent from './states/TranscriptionDone.vue';
import FailedStateComponent from './states/TranscriptionFailed.vue';
import ImportPendingStateComponent from './states/ImportPending.vue';
import BotConnectingStateComponent from './states/BotConnecting.vue';
import BotConnectionFailedStateComponent from './states/BotConnectionFailed.vue';
import TranscriptionInQueueStateComponent from './states/TranscriptionInQueue.vue';
import TranscriptionGenerationInProgressStateComponent from './states/TranscriptionGenerationInProgress.vue';

const props = defineProps<{
  meeting: MeetingDto;
}>();

const currentStateComponent = computed(() =>
  getStateComponent(props.meeting.status, props.meeting.name_platform),
);

function getStateComponent(status: MeetingStatus, name_platform: string) {
  switch (status) {
    case 'NONE':
      return NoneStateComponent;
    case 'CAPTURE_PENDING':
      if (name_platform === 'MCR_RECORD') {
        return RecordingInProgressStateComponent;
      }
      return BotConnectingStateComponent;
    case 'IMPORT_PENDING':
      return ImportPendingStateComponent;
    case 'CAPTURE_BOT_IS_CONNECTING':
      return BotConnectingStateComponent;
    case 'CAPTURE_BOT_CONNECTION_FAILED':
      return BotConnectionFailedStateComponent;
    case 'CAPTURE_IN_PROGRESS':
      if (name_platform === 'MCR_RECORD') {
        return RecordingInProgressStateComponent;
      }
      return InProgressStateComponent;
    case 'CAPTURE_DONE':
    case 'TRANSCRIPTION_PENDING':
      return TranscriptionInQueueStateComponent;
    case 'TRANSCRIPTION_IN_PROGRESS':
      return TranscriptionGenerationInProgressStateComponent;
    case 'TRANSCRIPTION_DONE':
    case 'REPORT_PENDING':
    case 'REPORT_DONE':
      return DoneStateComponent;
    case 'CAPTURE_FAILED':
    case 'TRANSCRIPTION_FAILED':
      return FailedStateComponent;
    default:
      return NoneStateComponent;
  }
}
</script>
