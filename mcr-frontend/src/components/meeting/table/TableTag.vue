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
      class: 'info',
      label: t('meetings.status.IN_PROGRESS'),
    };
  }

  if (isMeetingFailed(meeting.status)) {
    return {
      class: 'error',
      label: t('meetings.status.FAILED'),
    };
  }

  if (meeting.status === 'NONE') {
    return {
      class: 'pending',
      label: t('meetings.status.NONE'),
    };
  }

  if (meeting.name_platform === 'MCR_IMPORT') {
    return {
      class: 'import',
      label: t('meetings.status.DONE_IMPORT'),
    };
  }

  return {
    class: 'success',
    label: t('meetings.status.DONE'),
  };
}
</script>

<style>
.fr-tag.info {
  color: var(--info-425-625);
  background-color: var(--info-950-100);
}

.fr-tag.pending {
  background-color: var(--yellow-tournesol-950-100);
  color: var(--yellow-tournesol-sun-407-moon-922);
}

.fr-tag.success {
  color: var(--success-425-625);
  background-color: var(--success-950-100);
}

.fr-tag.error {
  color: var(--error-425-625);
  background-color: var(--error-950-100);
}

.fr-tag.import {
  color: var(--purple-glycine-sun-319-moon-630);
  background-color: var(--purple-glycine-925-125);
}
</style>
