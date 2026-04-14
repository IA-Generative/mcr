<template>
  <RouterLink :to="`${ROUTES.MEETINGS.path}/${cell.id}`">
    {{ cell.name }}
  </RouterLink>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router';
import { ROUTES } from '@/router/routes';
import type { MeetingTitleCell } from '../types';

defineProps<{ cell: MeetingTitleCell }>();
</script>
