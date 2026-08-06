<script lang="ts" setup>
import type { Message } from '@/composables/use-toaster';

defineProps<{ messages: Message[] }>();

const emit = defineEmits<{
  closeMessage: [id: string];
}>();

const close = (id: string) => emit('closeMessage', id);
</script>

<template>
  <!-- The stacking index matches .fr-modal's, so toasts stay above an open modal -->
  <div class="pointer-events-none fixed bottom-4 z-[1750] w-full">
    <TransitionGroup
      mode="out-in"
      name="list"
      tag="div"
      class="flex flex-col items-center"
    >
      <template
        v-for="message in messages"
        :key="message.id"
      >
        <DsfrAlert
          class="pointer-events-auto w-[90%] bg-grey-1000"
          v-bind="message"
          @close="close(message.id as string)"
        />
      </template>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.list-move, /* apply transition to moving elements */
.list-enter-active,
.list-leave-active {
  transition: all 0.5s ease;
}

.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateY(30px);
}

/* ensure leaving items are taken out of layout flow so that moving
   animations can be calculated correctly. */
.list-leave-active {
  position: fixed;
}
</style>
