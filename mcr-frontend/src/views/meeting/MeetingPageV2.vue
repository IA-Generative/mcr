<template>
  <div class="fr-container py-5 flex flex-col h-full">
    <div v-if="meeting">
      <div class="flex flex-row items-center justify-between">
        <MeetingFrontMatterV2 :meeting="meeting" />
      </div>
    </div>

    <div
      v-else-if="isLoading"
      class="flex items-center justify-center h-full"
    >
      <VIcon
        name="ri-loader-3-line"
        animation="spin"
        scale="3"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ROUTES } from '@/router/routes';
import { is403Error, is404Error } from '@/services/http/http.utils';
import { useMeetings } from '@/services/meetings/use-meeting';

const router = useRouter();
const route = useRoute();
const { id } = route.params;

const { getMeetingQuery } = useMeetings();
const { data: meeting, error, isError, isLoading } = getMeetingQuery(Number(id as string));

watch(isError, () => {
  if (isError.value && (is403Error(error.value) || is404Error(error.value))) {
    router.push({ name: ROUTES.NOT_FOUND.name });
    return;
  }
});
</script>
