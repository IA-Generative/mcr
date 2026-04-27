<template>
  <div class="flex flex-col flex-1">
    <div class="fr-container py-5 flex flex-col">
      <div v-if="meeting">
        <div class="flex flex-row items-center justify-between">
          <MeetingFrontMatterV2 :meeting="meeting" />
        </div>
      </div>

      <div
        v-else-if="isLoading"
        class="flex items-center justify-center h-full"
      >
        <VIcon
          name="ri-loader-3-line"
          animation="spin"
          scale="3"
        />
      </div>
    </div>

    <div class="content-container flex-1">
      <div class="fr-container py-5 flex flex-col h-full">
        <DsfrAlert
          v-if="showAlert && peremptionDays !== undefined"
          :type="alertType"
          closeable
          data-testid="alert-availability"
          @close="closeAlert"
        >
          {{ t('meeting-v2.deletion-warning', peremptionDays) }}
        </DsfrAlert>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useSessionAlert } from '@/composables/use-session-alert';
import { t } from '@/plugins/i18n';
import { ROUTES } from '@/router/routes';
import { is403Error, is404Error } from '@/services/http/http.utils';
import { useMeetings } from '@/services/meetings/use-meeting';
import type { DsfrAlertType } from '@gouvminint/vue-dsfr';
import { differenceInDays, parseISO } from 'date-fns';

const router = useRouter();
const route = useRoute();
const { id } = route.params;

const { getMeetingQuery } = useMeetings();
const { data: meeting, error, isError, isLoading } = getMeetingQuery(Number(id as string));

watch(isError, () => {
  if (isError.value && (is403Error(error.value) || is404Error(error.value))) {
    router.push({ name: ROUTES.NOT_FOUND.name });
    return;
  }
});

const { showAlert, closeAlert } = useSessionAlert('meeting-page-dsfr-alert-closed');

const peremptionDays = computed(() => {
  if (meeting.value?.creation_date === undefined) {
    return undefined;
  }
  const thirtyDaysAgo = new Date();
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
  const days = differenceInDays(parseISO(meeting.value.creation_date), thirtyDaysAgo);
  return days >= 0 ? days : undefined;
});

watch(peremptionDays, (days) => {
  if (days === undefined && meeting.value?.creation_date !== undefined) {
    closeAlert();
  }
});

const alertType = computed<DsfrAlertType>(() => {
  return peremptionDays.value !== undefined && peremptionDays.value > 10 ? 'info' : 'warning';
});
</script>

<style scoped>
.content-container {
  background-color: var(--beige-gris-galet-950-100);
}
</style>
