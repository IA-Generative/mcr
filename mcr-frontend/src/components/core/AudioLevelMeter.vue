<template>
  <div
    class="flex items-center gap-2"
    aria-label="audio-level-meter"
  >
    <span
      class="fr-icon-mic-fill text-[var(--blue-france-sun-113-625)]"
      aria-hidden="true"
    ></span>
    <div class="w-40 h-2 bg-[var(--grey-950-100)] rounded overflow-hidden">
      <div
        class="h-full bg-[var(--blue-france-sun-113-625)]"
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
