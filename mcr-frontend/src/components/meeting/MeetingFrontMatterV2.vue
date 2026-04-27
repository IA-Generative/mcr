<template>
  <div class="flex flex-col gap-4">
    <DsfrBreadcrumb
      :links="[
        { text: 'Accueil', to: '/meetings' },
        { text: meeting.name, to: `/meetings/${meeting.id}` },
      ]"
    />
    <h1 class="fr-text text-4xl font-bold text truncate-title">{{ meeting.name }}</h1>
    <div class="text">
      <span>{{ getSubtitleFromPlatformName(meeting.name_platform) }}</span>
      <span class="font-semibold">{{ getCalendarDateFromIso8601(meeting.creation_date) }} </span>
      <span> à </span>
      <span class="font-semibold">{{ getTimeFromIso8601(meeting.creation_date) }}</span>
      <span class="ml-4 mr-4">|</span>
      <span>Durée : </span>
      <span class="font-semibold">{{ getMeetingDuration(meeting) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { t } from '@/plugins/i18n';
import {
  getCalendarDateFromIso8601,
  getMeetingDuration,
  getTimeFromIso8601,
} from '@/services/meetings/meetings-datetime';
import type { AllMeetingPlatforms, MeetingDetailDto } from '@/services/meetings/meetings.types';
import { DsfrBreadcrumb } from '@gouvminint/vue-dsfr';

defineProps<{
  meeting: MeetingDetailDto;
}>();

function getSubtitleFromPlatformName(namePlatform: AllMeetingPlatforms): string {
  switch (namePlatform) {
    case 'MCR_IMPORT':
      return t('meeting-v2.subtitle.import');
    case 'MCR_RECORD':
      return t('meeting-v2.subtitle.record');
    default:
      return t('meeting-v2.subtitle.visio', { visioPlatform: namePlatform });
  }
}
</script>

<style scoped>
.text {
  color: var(--grey-200-850);
}

.truncate-title {
  max-width: 70vw;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

:deep(.fr-breadcrumb) {
  margin: 0;
}

:deep(.fr-breadcrumb__link) {
  display: inline-block;
  max-width: 25vw;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  vertical-align: super;
}

:deep(.fr-breadcrumb__list li:not(:first-child):before) {
  display: inline-flex;
  vertical-align: super;
}
</style>
