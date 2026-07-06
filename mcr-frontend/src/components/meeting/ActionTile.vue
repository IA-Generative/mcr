<template>
  <DsfrButton
    secondary
    class="p-6 pb-7 shadow-[inset_0_-0.25rem_0_0_var(--border-active-blue-france),inset_0_0_0_1px_var(--border-default-grey)] [&>span]:flex [&>span]:size-full"
  >
    <span class="flex size-full items-center gap-4">
      <img
        :src="imgSrc"
        alt=""
        class="size-16 shrink-0"
      />

      <span class="flex flex-col gap-1 text-left">
        <span class="text-base font-bold leading-6 text-primary">
          {{ title }}
        </span>

        <span class="text-sm leading-6 text-grey">
          {{ description }}
        </span>
      </span>
    </span>
  </DsfrButton>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
  description: string;
  imgSrc: string;
}>();
</script>
