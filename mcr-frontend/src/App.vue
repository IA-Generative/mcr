<script setup lang="ts">
import useToaster from './composables/use-toaster';
import { VueQueryDevtools } from '@tanstack/vue-query-devtools';
import AppToaster from '@/components/core/AppToaster.vue';
import AppHeader from './components/core/AppHeader.vue';
import AppFooter from './components/core/AppFooter.vue';
import { useAuth } from './components/sign-in/use-auth';
import { ModalsContainer } from 'vue-final-modal';

useScheme({ scheme: 'light' });

const toaster = useToaster();
const auth = useAuth();
provide('auth', auth);

onMounted(async () => {
  await auth.currentUserQuery.refetch();
});
</script>

<template>
  <div class="flex flex-col h-screen">
    <AppHeader></AppHeader>
    <main class="flex-grow">
      <router-view />
    </main>
    <AppFooter></AppFooter>
  </div>
  <ModalsContainer />
  <AppToaster
    :messages="toaster.messages"
    @close-message="toaster.removeMessage($event)"
  />
  <VueQueryDevtools />
</template>
