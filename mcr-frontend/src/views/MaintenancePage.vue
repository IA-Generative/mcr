<template>
  <div class="flex flex-col items-center justify-center h-full py-10 text-center gap-6">
    <img
      :src="maintenanceArtwork"
      :alt="$t('maintenance.title')"
      class="w-40 h-40"
    />
    <div class="flex flex-col gap-2 max-w-2xl">
      <h1 class="fr-h1">{{ $t('maintenance.title') }}</h1>
      <p class="fr-text--lead">{{ $t('maintenance.description') }}</p>
      <p class="fr-text--lead">{{ $t('maintenance.description2') }}</p>
      <p class="fr-text--sm">{{ $t('maintenance.description3') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import maintenanceArtwork from '@dsfr-artwork/pictograms/system/system.svg?url';
</script>

<style scoped></style>
