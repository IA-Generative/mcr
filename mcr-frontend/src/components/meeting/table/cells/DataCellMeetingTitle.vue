<template>
  <span
    v-if="isInAlertPeriod"
    class="tooltip-wrapper"
  >
    <DsfrTooltip
      :content="tooltipContent"
      :on-hover="true"
    >
      <span class="fr-icon-warning-line fr-icon--sm" />
    </DsfrTooltip>
  </span>
  <RouterLink
    :to="`${ROUTES.MEETINGS.path}/${meeting.id}`"
    class="fr-link"
  >
    {{ meetingTitle }}
  </RouterLink>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router';
import { ROUTES } from '@/router/routes';
import type { MeetingTitleCell } from '../types';
import { useMeetingPeremption } from '@/composables/use-meeting-peremption';
import { t } from '@/plugins/i18n';

const { cell: meeting } = defineProps<{ cell: MeetingTitleCell }>();

const { isInAlertPeriod, daysBeforeDeletion } = useMeetingPeremption(() => meeting.creation_date);

const tooltipContent = computed(() => {
  const daysLeft = daysBeforeDeletion.value;
  if (daysLeft !== undefined && daysLeft > 1) {
    return t('meetings_v2.table.columns.title.tooltip', { daysLeft: daysLeft });
  } else {
    return t('meetings_v2.table.columns.title.tooltip-expired');
  }
});

const meetingTitle = computed(() => {
  if (isInAlertPeriod.value) {
    return ' ' + meeting.name;
  } else {
    return meeting.name;
  }
});
</script>

<style scoped>
.fr-link {
  font-size: 0.875rem;
}

.tooltip-wrapper :deep(.fr-link) {
  font-size: 0.875rem;
}
</style>
