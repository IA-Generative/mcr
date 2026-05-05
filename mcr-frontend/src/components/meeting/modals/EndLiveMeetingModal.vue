<template>
  <BaseModal
    :modal-id="END_LIVE_MEETING_MODAL_ID"
    :title="$t('meeting-v2.recording.ending.title')"
    size="lg"
    class="max-sm:p-4"
  >
    <div>
      <ul class="list-disc pl-8 mb-6">
        <li>
          {{ $t('meeting-v2.recording.ending.description') }}
        </li>
      </ul>
    </div>
    <template #footer>
      <div class="flex w-full justify-end gap-4">
        <DsfrButton
          secondary
          :label="$t('meeting-v2.recording.ending.buttons.cancel')"
          @click="close"
        />
        <DsfrButton
          :label="$t('meeting-v2.recording.ending.buttons.end')"
          icon="fr-icon-stop-circle-fill"
          @click="terminateMeeting"
        />
      </div>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import BaseModal from '@/components/core/BaseModal.vue';
import { useVfm } from 'vue-final-modal';

const END_LIVE_MEETING_MODAL_ID = 'end-live-meeting-modal';
const close = () => useVfm().close(END_LIVE_MEETING_MODAL_ID);

const emit = defineEmits<{
  (e: 'success'): void;
}>();

function terminateMeeting() {
  emit('success');
  close();
}
</script>
