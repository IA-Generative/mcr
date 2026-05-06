<template>
  <DsfrTag
    :label="tagMeta.label"
    :class="tagMeta.class"
  />
</template>

<script lang="ts" setup>
import {
  isMeetingFailed,
  isMeetingInProgress,
  type MeetingDto,
} from '@/services/meetings/meetings.types';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
const props = defineProps<{
  meeting: MeetingDto;
}>();

const tagMeta = computed(() => getTagMeta(props.meeting));

function getTagMeta(meeting: MeetingDto) {
  if (isMeetingInProgress(meeting.status)) {
    return {
      class: 'bg-info-950 text-info-425',
      label: t('meetings.status.IN_PROGRESS'),
    };
  }

  if (isMeetingFailed(meeting.status)) {
    return {
      class: 'bg-error-950 text-error-425',
      label: t('meetings.status.FAILED'),
    };
  }

  if (meeting.status === 'NONE') {
    return {
      class: 'bg-yellow-tournesol-950 text-yellow-tournesol-sun',
      label: t('meetings.status.NONE'),
    };
  }

  if (meeting.name_platform === 'MCR_IMPORT') {
    return {
      class: 'bg-purple-glycine-925 text-purple-glycine-sun',
      label: t('meetings.status.DONE_IMPORT'),
    };
  }

  return {
    class: 'bg-success-950 text-success-425',
    label: t('meetings.status.DONE'),
  };
}
</script>
