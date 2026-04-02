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
        :title="t('meeting-v2.tile-import.title')"
        :description="t('meeting-v2.tile-import.subtitle')"
      />
    </div>
  </div>
</template>

<script lang="ts" setup>
import PageFrontMatterV2 from '@/components/core/PageFrontMatterV2.vue';
import { t } from '@/plugins/i18n';
import videoSvgPath from '@dsfr-artwork/pictograms/leisure/video.svg?url';
</script>

<style scoped>
.tile {
  width: 363px;
  height: 176px;
}
</style>
