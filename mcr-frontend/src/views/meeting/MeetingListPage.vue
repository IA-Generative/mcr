<template>
  <div class="fr-container py-5 flex w-full flex-col gap-10">
    <PageFrontMatter
      :title="$t('meetings_v2.hero.title')"
      :subtitle="$t('meetings_v2.hero.subtitle')"
    />

    <MeetingTiles />
  </div>

  <div class="w-full bg-[--blue-france-975-75]">
    <div class="fr-container py-5 flex w-full flex-col gap-10">
      <PageFrontMatter
        :title="$t('meetings_v2.table.new-title')"
        :subtitle="$t('meetings_v2.table.new-subtitle')"
      />
      <DsfrAlert
        v-if="showAlert"
        type="info"
        closeable
        data-testid="alert-availability"
        role="alertInfo"
        @close="closeAlert"
      >
        <p>
          {{ $t('meetings_v2.availability-alert-description.audio') }}
          <span style="font-weight: bold">
            {{ MAX_DELAY_TO_FETCH_AUDIO }}
            {{ $t('meetings_v2.availability-alert-description.days') }}
          </span>
        </p>
        <p>
          {{ $t('meetings_v2.availability-alert-description.pre-warning-pre-bold') }}
          <span style="font-weight: bold">
            {{ MAX_DELAY_TO_FETCH_DELIVERABLE }}
            {{ $t('meetings_v2.availability-alert-description.days') }}
          </span>
          {{ $t('meetings_v2.availability-alert-description.pre-warning-post-bold') }}
          <span
            class="fr-icon-warning-line"
            aria-hidden="true"
            style="color: var(--blue-france-sun-113-625)"
          ></span>
          {{ $t('meetings_v2.availability-alert-description.post-warning') }}
        </p>
      </DsfrAlert>
    </div>

    <MeetingsDataTable />
  </div>
</template>

<script lang="ts" setup>
import PageFrontMatter from '@/components/core/PageFrontMatter.vue';
import { MAX_DELAY_TO_FETCH_AUDIO, MAX_DELAY_TO_FETCH_DELIVERABLE } from '@/config/meeting';
import MeetingTiles from './MeetingTiles.vue';

const SESSION_KEY = 'dsfr-alert-closed';
const showAlert = ref(true);
const CLOSED_ALERT_VALUE = 'CLOSED_ALERT';

onMounted(() => {
  const alreadyClosed = sessionStorage.getItem(SESSION_KEY);
  if (alreadyClosed && alreadyClosed == CLOSED_ALERT_VALUE) {
    showAlert.value = false;
  }
});

function closeAlert() {
  showAlert.value = false;
  sessionStorage.setItem(SESSION_KEY, CLOSED_ALERT_VALUE);
}
</script>
