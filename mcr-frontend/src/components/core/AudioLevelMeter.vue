<template>
  <div
    class="flex items-center gap-2"
    aria-label="audio-level-meter"
  >
    <span
      class="fr-icon-mic-fill text-blue-france-sun"
      aria-hidden="true"
    ></span>
    <div class="w-40 h-2 bg-grey-950 rounded overflow-hidden">
      <div
        class="h-full bg-blue-france-sun"
        :style="{ width: `${props.level * 100}%` }"
      />
    </div>
  </div>
</template>

<script lang="ts" setup>
const props = defineProps<{
  level: number;
}>();
</script>
