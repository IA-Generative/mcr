<template>
  <span class="hover-tooltip-host">
    <slot />
    <span
      class="hover-tooltip"
      role="tooltip"
    >
      {{ content }}
    </span>
  </span>
</template>

<script setup lang="ts">
defineProps<{ content: string }>();
</script>

<style scoped>
.hover-tooltip-host {
  position: relative;
  display: inline-flex;
}

.hover-tooltip {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  background: var(--background-overlap-grey, #ffffff);
  color: var(--text-default-grey);
  border: 1px solid var(--border-default-grey);
  border-radius: 4px;
  padding: 0.5rem 0.75rem;
  font-size: 0.75rem;
  line-height: 1.25rem;
  white-space: nowrap;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s;
  z-index: 1000;
}

.hover-tooltip-host:hover .hover-tooltip,
.hover-tooltip-host:focus-within .hover-tooltip {
  opacity: 1;
}
</style>
