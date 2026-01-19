<template>
  <div class="flex flex-col">
    <h1 class="fr-text--lg m-0">{{ name }}</h1>
    <h2 class="fr-text--sm text-body-grey">
      {{ `${$t(getSubtitleFromPlatformName(namePlatform))} ${formatMeetingDate(startDate)}` }}
    </h2>
  </div>
</template>

<script lang="ts" setup>
import type { MessageKeys } from '@/plugins/i18n';
import type { AllMeetingPlatforms } from '@/services/meetings/meetings.types';
import { formatMeetingDate } from '@/utils/formatters';

defineProps<{
  name: string;
  namePlatform: AllMeetingPlatforms;
  startDate: string;
}>();

function getSubtitleFromPlatformName(namePlatform: AllMeetingPlatforms): MessageKeys {
  switch (namePlatform) {
    case 'MCR_IMPORT':
      return 'meeting.subtitle.imported';
    case 'MCR_RECORD':
      return 'meeting.subtitle.recorded';
    default:
      return 'meeting.subtitle.scheduled';
  }
}
</script>
