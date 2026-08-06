<template>
  <div class="flex h-full flex-col items-center justify-center gap-6 py-10 text-center">
    <img
      :src="maintenanceArtwork"
      :alt="$t('maintenance.title')"
      class="h-40 w-40"
    />
    <div class="flex max-w-2xl flex-col gap-2">
      <h1 class="fr-h1">{{ $t('maintenance.title') }}</h1>
      <p class="fr-text--lead">{{ $t('maintenance.description') }}</p>
      <p class="fr-text--lead">{{ $t('maintenance.description-2') }}</p>
      <p class="fr-text--sm">{{ $t('maintenance.description-3') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import maintenanceArtwork from '@dsfr-artwork/pictograms/system/system.svg?url';
</script>

<style scoped></style>
