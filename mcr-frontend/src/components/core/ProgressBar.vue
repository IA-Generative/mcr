<template>
  <div
    class="h-2 w-4/5 overflow-hidden rounded-full bg-background-contrast-grey"
    role="progressbar"
    :aria-valuenow="progress"
    aria-valuemin="0"
    aria-valuemax="100"
    :aria-busy="progress < 100"
  >
    <div
      class="h-full bg-primary transition-[width] duration-1000 ease-linear"
      :style="{ width: `${progress}%` }"
    ></div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  progress: number;
}>();
</script>
