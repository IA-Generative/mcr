<template>
  <span
    class="relative inline-flex size-6"
    :role="complete ? 'img' : 'progressbar'"
    :aria-label="label"
    :aria-valuenow="complete ? undefined : percent"
    :aria-valuemin="complete ? undefined : 0"
    :aria-valuemax="complete ? undefined : 100"
  >
    <svg
      viewBox="0 0 36 36"
      class="size-full -rotate-90"
      aria-hidden="true"
    >
      <circle
        class="fill-none stroke-[var(--border-default-grey)]"
        cx="18"
        cy="18"
        :r="RADIUS"
        stroke-width="3"
      />
      <circle
        class="fill-none transition-all duration-[400ms] ease-linear"
        :class="complete ? 'stroke-success-425' : 'stroke-blue-france-sun'"
        cx="18"
        cy="18"
        :r="RADIUS"
        stroke-width="3"
        stroke-linecap="round"
        :stroke-dasharray="CIRCUMFERENCE"
        :style="{ strokeDashoffset: dashOffset }"
      />
    </svg>
    <svg
      viewBox="0 0 36 36"
      class="absolute inset-0 size-full stroke-success-425 opacity-0 transition-opacity delay-[400ms] duration-200"
      :class="{ 'opacity-100': complete }"
      aria-hidden="true"
    >
      <path
        class="fill-none"
        d="M11.5 18.5 L16 23 L24.5 13.5"
        stroke-width="3"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </svg>
  </span>
</template>

<script setup lang="ts">
const RADIUS = 15;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

const props = defineProps<{
  ratio: number;
  complete: boolean;
  label: string;
}>();

const clampedRatio = computed(() => Math.min(1, Math.max(0, props.complete ? 1 : props.ratio)));
const percent = computed(() => Math.round(clampedRatio.value * 100));
const dashOffset = computed(() => CIRCUMFERENCE * (1 - clampedRatio.value));
</script>
