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
          v-if="showAlert && daysBeforeDeletion !== undefined"
          :type="alertType"
          closeable
          data-testid="alert-availability"
          @close="closeAlert"
        >
          {{ t('meeting-v2.deletion-warning', daysBeforeDeletion) }}
        </DsfrAlert>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useMeetingPeremption } from '@/composables/use-meeting-peremption';
import { useSessionAlert } from '@/composables/use-session-alert';
import { t } from '@/plugins/i18n';
import { ROUTES } from '@/router/routes';
import { is403Error, is404Error } from '@/services/http/http.utils';
import { useMeetings } from '@/services/meetings/use-meeting';

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
const { daysBeforeDeletion, alertType } = useMeetingPeremption(() => meeting.value?.creation_date);

watch(daysBeforeDeletion, (days) => {
  if (days === undefined && meeting.value?.creation_date !== undefined) {
    closeAlert();
  }
});
</script>

<style scoped>
.content-container {
  background-color: var(--beige-gris-galet-950-100);
}
</style>
