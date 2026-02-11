<template>
  <div class="fr-container py-5 flex w-full flex-col gap-10">
    <PageFrontMatterV2
      :title="$t('meetings_v2.hero.title')"
      :subtitle="$t('meetings_v2.hero.subtitle')"
    />
  </div>
</template>

<script lang="ts" setup>
import PageFrontMatterV2 from '@/components/core/PageFrontMatterV2.vue';
</script>
