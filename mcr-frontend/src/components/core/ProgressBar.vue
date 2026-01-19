<template>
  <div
    class="progress-container"
    role="progressbar"
    :aria-valuenow="progress"
    aria-valuemin="0"
    aria-valuemax="100"
    :aria-busy="progress < 100"
  >
    <div
      class="progress-bar"
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
  background-color: var(--background-contrast-grey);
  border-radius: 9999px;
  overflow: hidden;
  width: 80%;
}
.progress-bar {
  height: 100%;
  background-color: var(--background-action-high-blue-france);
  transition: width 1s linear;
}
</style>
