<template>
  <div class="flex flex-col gap-4">
    <DsfrBreadcrumb
      :links="[
        { text: $t('home.text'), to: '/meetings' },
        { text: meeting.name, to: `/meetings/${meeting.id}` },
      ]"
    />
    <h1
      class="fr-text text-4xl font-bold text-grey-200 max-w-[50vw] overflow-hidden whitespace-nowrap text-ellipsis"
    >
      {{ meeting.name }}
    </h1>
    <div class="text-grey-200">
      <i18n-t
        keypath="meeting-v2.details"
        tag="span"
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
      </i18n-t>
      <template v-if="meetingDuration">
        <span class="ml-4 mr-4">{{ t('common.pipe') }}</span>
        <i18n-t
          keypath="meeting-v2.duration-label"
          tag="span"
        >
          <template #duration>
            <span class="font-semibold">{{ meetingDuration }}</span>
          </template>
        </i18n-t>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { t } from '@/plugins/i18n';
import {
  getCalendarDateFromIso8601,
  calculateDuration,
  getTimeFromIso8601,
} from '@/services/meetings/meetings-datetime';
import type { AllMeetingPlatforms, MeetingDetailDto } from '@/services/meetings/meetings.types';
import { DsfrBreadcrumb } from '@gouvminint/vue-dsfr';

const props = defineProps<{
  meeting: MeetingDetailDto;
}>();

const meetingDuration = computed(
  () => calculateDuration(props.meeting.start_date, props.meeting.end_date) || undefined,
);

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
