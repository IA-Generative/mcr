<template>
  <div class="flex flex-col gap-4">
    <DsfrBreadcrumb
      :links="[
        { text: $t('home.text'), to: '/meetings' },
        { text: meeting.name, to: `/meetings/${meeting.id}` },
      ]"
    />
    <h1 class="fr-text text-4xl font-bold text-grey-200 truncate-title">{{ meeting.name }}</h1>
    <i18n-t
      keypath="meeting-v2.details"
      tag="div"
      class="text-grey-200"
    >
      <template #subtitle>
        <span>{{ getSubtitleFromPlatformName(meeting.name_platform) }}</span>
      </template>
      <template #date>
        <span class="font-semibold">{{ getCalendarDateFromIso8601(meeting.creation_date) }}</span>
      </template>
      <template #time>
        <span class="font-semibold">{{ getTimeFromIso8601(meeting.creation_date) }}</span>
      </template>
      <template #separator>
        <span class="ml-4 mr-4">{{ t('common.pipe') }}</span>
      </template>
      <template #duration>
        <span class="font-semibold">{{ getMeetingDuration(meeting) }}</span>
      </template>
    </i18n-t>
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
.truncate-title {
  max-width: 50vw;
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
