<template>
  <div class="fr-container py-5 flex w-full flex-col gap-10">
    <PageFrontMatterV2
      :title="$t('meetings_v2.hero.title')"
      :subtitle="$t('meetings_v2.hero.subtitle')"
    />

    <div class="tile-container">
      <DsfrTile
        class="tile"
        :horizontal="true"
        :small="true"
        :svg-path="videoSvgPath"
        :title="t('meetings_v2.tile-import.title')"
        :description="t('meetings_v2.tile-import.subtitle')"
      />
      <DsfrTile
        class="tile"
        :horizontal="true"
        :small="true"
        :svg-path="podcastSvgPath"
        :title="t('meetings_v2.tile-record.title')"
        :description="t('meetings_v2.tile-record.subtitle')"
      />
      <DsfrTile
        class="tile"
        :horizontal="true"
        :small="true"
        :svg-path="selfTrainingSvgPath"
        :title="t('meetings_v2.tile-visio.title')"
        :description="
          isWebexEnabled
            ? t('meetings_v2.tile-visio.subtitle-with-webex')
            : t('meetings_v2.tile-visio.subtitle-without-webex')
        "
      />
    </div>
  </div>
  <div class="fr-container py-5 flex w-full flex-col gap-10">
    <div class="fr-container bg-[--blue-france-975-75]">
      <PageFrontMatterV2
        :title="$t('meetings_v2.table.new-title')"
        :subtitle="$t('meetings_v2.table.new-subtitle')"
      />
      <DsfrAlert
        type="info"
        closeable
        @close="closeAlert"
        data-testid="alert-availability"
        >
        <p>
          {{ $t('meetings_v2.availability-alert-description.audio') }}
          <span style="font-weight: bold"> 
            {{MAX_DELAY_TO_FETCH_AUDIO}} {{ $t('meetings_v2.availability-alert-description.audio-bold') }} 
          </span>
        </p>
        <p>
          {{ $t('meetings_v2.availability-alert-description.pre-warning-pre-bold') }}
          <span style="font-weight: bold"> 
            {{MAX_DELAY_TO_FETCH_DELIVERABLE}} {{ $t('meetings_v2.availability-alert-description.pre-warning-bold') }} 
          </span>
          {{ $t('meetings_v2.availability-alert-description.pre-warning-post-bold') }}
          <span class="fr-icon-warning-line" aria-hidden="true" style="color:var(--blue-france-sun-113-625)"></span>
          {{ $t('meetings_v2.availability-alert-description.post-warning') }}
      </p>
      </DsfrAlert>
    </div>
  </div>
</template>

<script lang="ts" setup>
import PageFrontMatterV2 from '@/components/core/PageFrontMatterV2.vue';
import { useFeatureFlag } from '@/composables/use-feature-flag';
import { t } from '@/plugins/i18n';
import videoSvgPath from '@dsfr-artwork/pictograms/leisure/video.svg?url';
import podcastSvgPath from '@dsfr-artwork/pictograms/leisure/podcast.svg?url';
import selfTrainingSvgPath from '@dsfr-artwork/pictograms/digital/self-training.svg?url';

const isWebexEnabled = useFeatureFlag('webex');
import { ref, onMounted } from 'vue'
import {MAX_DELAY_TO_FETCH_AUDIO, MAX_DELAY_TO_FETCH_DELIVERABLE} from '@/config/meeting';

const SESSION_KEY = 'dsfr-alert-closed'
const showAlert = ref(true)
const CLOSED_ALERT_VALUE = "CLOSED_ALERT"


onMounted(() => {
  const alreadyClosed = sessionStorage.getItem(SESSION_KEY)
  if (alreadyClosed && alreadyClosed == CLOSED_ALERT_VALUE) {
    showAlert.value = false
  }
})

function closeAlert() {
  showAlert.value = false
  sessionStorage.setItem(SESSION_KEY, CLOSED_ALERT_VALUE)
}
</script>

<style scoped>
.tile-container {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.tile {
  width: 95vw;
  height: 20vh;
}

@media (min-width: 440px) {
  .tile {
    width: 95vw;
    height: 15vh;
  }
}

@media (min-width: 1040px) {
  .tile-container {
    flex-direction: row;
  }

  .tile {
    width: 30vw;
    height: 20vh;
  }
}
</style>

