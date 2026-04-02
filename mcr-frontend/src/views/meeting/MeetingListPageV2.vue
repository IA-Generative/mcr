<template>
  <div class="fr-container py-5 flex w-full flex-col gap-10">
    <PageFrontMatterV2
      :title="$t('meetings_v2.hero.title')"
      :subtitle="$t('meetings_v2.hero.subtitle')"
    />

    <div class="flex flex-row gap-[18px]">
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
</template>

<script lang="ts" setup>
import PageFrontMatterV2 from '@/components/core/PageFrontMatterV2.vue';
import { useFeatureFlag } from '@/composables/use-feature-flag';
import { t } from '@/plugins/i18n';
import videoSvgPath from '@dsfr-artwork/pictograms/leisure/video.svg?url';
import podcastSvgPath from '@dsfr-artwork/pictograms/leisure/podcast.svg?url';
import selfTrainingSvgPath from '@dsfr-artwork/pictograms/digital/self-training.svg?url';

const isWebexEnabled = useFeatureFlag('webex');
</script>

<style scoped>
.tile {
  width: 363px;
  height: 176px;
}
</style>
