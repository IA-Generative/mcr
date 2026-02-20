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
