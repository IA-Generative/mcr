<template>
  <StatusTag :status="status as DeliverableStatus" />
</template>

<script lang="ts">
import { DeliverableStatus } from '@/services/deliverables/deliverables.types';
</script>
<script lang="ts" setup>
defineProps<{
  status: DeliverableStatus | null;
}>();
</script>
