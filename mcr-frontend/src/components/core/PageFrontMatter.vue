<template>
  <div class="flex flex-col">
    <h1 class="fr-h2 mb-3">{{ title }}</h1>
    <span class="text-body-black">{{ subtitle }}</span>
  </div>
</template>

<script lang="ts" setup>
defineProps<{
  title?: string;
  subtitle?: string;
}>();
</script>
