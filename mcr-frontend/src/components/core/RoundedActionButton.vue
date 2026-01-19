<template>
  <button class="flex flex-col items-center gap-2">
    <VIcon
      :name="icon"
      scale="2.5"
      color="var(--blue-france-sun-113-625)"
    />
    <span class="font-bold text-[var(--blue-france-sun-113-625)]">
      <slot />
    </span>
  </button>
</template>

<script lang="ts" setup>
defineProps<{
  icon: string;
}>();
</script>
