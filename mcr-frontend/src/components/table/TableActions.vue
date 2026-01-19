<template>
  <div class="flex">
    <DsfrButton
      v-if="onEdit"
      icon="ri-pencil-line"
      icon-only
      no-outline
      tertiary
      @click="onEdit"
    />
    <DsfrButton
      v-if="onDelete"
      :icon="{ name: 'ri-delete-bin-line', fill: 'var(--error-425-625)' }"
      icon-only
      no-outline
      tertiary
      @click="onDelete"
    />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  onDelete?: () => void;
  onEdit?: () => void;
}>();
</script>

<style scoped></style>
