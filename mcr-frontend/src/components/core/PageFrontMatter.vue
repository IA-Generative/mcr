<template>
  <div class="flex flex-col">
    <h1 class="fr-h4 mb-3">{{ title }}</h1>
    <span class="text-body-grey">{{ subtitle }}</span>
  </div>
</template>

<script lang="ts" setup>
defineProps<{
  title?: string;
  subtitle?: string;
}>();
</script>
