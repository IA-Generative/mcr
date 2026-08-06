<template>
  <button
    class="flex flex-col items-center gap-2"
    :class="disabled && 'pointer-events-none cursor-not-allowed'"
    :aria-disabled="disabled || undefined"
  >
    <VIcon
      :name="icon"
      scale="2.5"
      :color="disabled ? 'var(--grey-625-425)' : 'var(--blue-france-sun-113-625)'"
    />
    <span
      class="flex flex-1 items-center text-center font-bold"
      :class="disabled ? 'text-grey-625' : 'text-blue-france-sun'"
    >
      <slot />
    </span>
  </button>
</template>

<script lang="ts" setup>
withDefaults(
  defineProps<{
    icon: string;
    disabled?: boolean;
  }>(),
  { disabled: false },
);
</script>
