<template>
  <div class="text-xl font-semibold pb-2">{{ $t('meeting-v2.visio-form.parameters') }}</div>
  <DsfrInputGroup
    :label="$t('meeting-v2.visio-form.meeting-title.title')"
    :hint="$t('meeting-v2.visio-form.meeting-title.example')"
    label-visible
  />
  <div class="pb-8">
    <span class="pb-2">
      {{ $t('meeting-v2.visio-form.visio-tools') }}
    </span>
    <DsfrSelect
      v-model="selectedPlatform"
      :options="meetingPlatformOptions"
      class="w-2/5"
    />
  </div>

  <div
    v-if="selectedPlatform !== null"
    class="pb-2"
  >
    <div class="text-xl font-semibold pb-2">
      {{ $t('meeting-v2.visio-form.connection.connection-title') }}
    </div>

    <div class="flex items-center fr-text-default--info pb-6">
      <span
        class="fr-icon-info-fill fr-icon--sm pr-1"
        aria-hidden="true"
      ></span>
      <span class="text-xs font-norm pr-1">{{
        $t('meeting-v2.visio-form.connection.connection-advice-1')
      }}</span>
      "
      <a
        class="text-xs font-norm"
        href="https://mirai.interieur.gouv.fr/outils-mirai/compte-rendu/bonnes-pratiques-fcr/"
        target="_blank"
        rel="noopener noreferrer"
      >
        {{ $t('meeting-v2.visio-form.connection.connection-redirection-text') }}
      </a>
      "
      <span class="text-xs font-norm pl-1">{{
        $t('meeting-v2.visio-form.connection.connection-advice-2')
      }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { OnlineMeetingPlatforms } from '@/services/meetings/meetings.types';

const platformLabels: Record<OnlineMeetingPlatforms, string> = {
  COMU: 'COMU',
  WEBINAIRE: "Webinaire de l'État",
  WEBCONF: 'Webconf',
  VISIO: 'Visio',
};

const meetingPlatformOptions = OnlineMeetingPlatforms.map((platform) => ({
  value: platform,
  text: platformLabels[platform],
}));
const selectedPlatform = ref<OnlineMeetingPlatforms | null>(null);
</script>

<style scoped>
:deep(.fr-notice) {
  background-color: transparent;
}

:deep(.fr-notice__title) {
  font-weight: normal;
}

:deep(a[target='_blank']::after) {
  display: none !important; /* enlève l'icône à droite */
}
</style>
