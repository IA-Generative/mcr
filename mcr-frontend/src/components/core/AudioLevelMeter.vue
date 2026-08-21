<template>
  <div
    class="flex items-center gap-2"
    aria-label="audio-level-meter"
  >
    <span
      class="fr-icon-mic-fill text-blue-france-sun"
      aria-hidden="true"
    ></span>
    <div class="h-2 w-40 overflow-hidden rounded-sm bg-grey-950">
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
