<template>
  <button
    class="flex flex-col items-center justify-center gap-2"
    :class="disabled && 'cursor-not-allowed pointer-events-none'"
    :aria-disabled="disabled || undefined"
  >
    <VIcon
      :name="icon"
      scale="2.5"
      :color="disabled ? 'var(--grey-625-425)' : 'var(--blue-france-sun-113-625)'"
    />
    <span
      class="font-bold"
      :class="disabled ? 'text-[var(--grey-625-425)]' : 'text-[var(--blue-france-sun-113-625)]'"
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
