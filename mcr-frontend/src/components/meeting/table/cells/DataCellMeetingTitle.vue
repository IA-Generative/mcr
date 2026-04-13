<template>
  <RouterLink :to="`${ROUTES.MEETINGS.path}/${typedCell.id}`">
    {{ typedCell.name }}
  </RouterLink>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router';
import { ROUTES } from '@/router/routes';

const props = defineProps<{ cell: unknown }>();
const typedCell = computed(() => props.cell as { name: string; id: number });
</script>
