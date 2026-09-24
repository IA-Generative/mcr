<template>
  <DsfrAlert
    v-if="pendingCount > 0"
    type="warning"
    :title="$t('meeting-v2.recovery.title')"
    data-testid="pending-chunks-card"
  >
    <p>{{ $t('meeting-v2.recovery.description', { count: pendingCount }) }}</p>
    <DsfrButton
      class="mt-4"
      :disabled="isRecovering"
      data-testid="pending-chunks-recover"
      @click="recover"
    >
      {{ isRecovering ? $t('meeting-v2.recovery.sending') : $t('meeting-v2.recovery.send') }}
    </DsfrButton>
  </DsfrAlert>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useChunkRecovery } from '@/composables/use-chunk-recovery';
import useToaster from '@/composables/use-toaster';
import { t } from '@/plugins/i18n';

const props = defineProps<{ meetingId: number }>();

const toaster = useToaster();
const { pendingCount, isRecovering, refreshPendingCount, recoverPendingChunks } = useChunkRecovery(
  props.meetingId,
);

onMounted(() => {
  refreshPendingCount();
});

async function recover() {
  const recovered = await recoverPendingChunks();
  if (recovered) {
    toaster.addSuccessMessage(t('meeting-v2.recovery.success'));
    return;
  }
  toaster.addErrorMessage(t('meeting-v2.recovery.failure'));
}
</script>
