<template>
  <div
    class="progress-container bg-background-contrast-grey"
    role="progressbar"
    :aria-valuenow="progress"
    aria-valuemin="0"
    aria-valuemax="100"
    :aria-busy="progress < 100"
  >
    <div
      class="progress-bar bg-primary"
      :style="{ width: `${progress}%` }"
    ></div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  progress: number;
}>();
</script>

<style scoped>
.progress-container {
  height: 0.5rem;
  border-radius: 9999px;
  overflow: hidden;
  width: 80%;
}
.progress-bar {
  height: 100%;
  transition: width 1s linear;
}
</style>
