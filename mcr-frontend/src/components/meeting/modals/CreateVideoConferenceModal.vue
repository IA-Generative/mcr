<template>
  <BaseModal
    :modal-id="CREATE_MEETING_MODAL_ID"
    :title="$t('meeting-v2.visio-form.title')"
    size="lg"
    class="visio-meeting-modal max-sm:p-4"
    no-actions
  >
    <div class="visio-meeting-modal-title-illustration">
      <img src="@dsfr-artwork/pictograms/digital/self-training.svg?url" />
    </div>
    <CreateVideoConferenceForm @submit="(dto: AddOnlineMeetingDto) => onSubmit(dto)" />
  </BaseModal>
</template>

<script setup lang="ts">
import BaseModal from '@/components/core/BaseModal.vue';
import { useVfm } from 'vue-final-modal';
import CreateVideoConferenceForm from '../CreateVideoConferenceForm.vue';
import type { AddOnlineMeetingDto } from '@/services/meetings/meetings.types';

const CREATE_MEETING_MODAL_ID = 'meeting-visio-modal-V2';
const close = () => useVfm().close(CREATE_MEETING_MODAL_ID);

const emit = defineEmits<{
  (e: 'createMeeting', payload: AddOnlineMeetingDto): void;
}>();

function onSubmit(dto: AddOnlineMeetingDto) {
  emit('createMeeting', dto);
  close();
}
</script>

<style scoped>
:global(#meeting-visio-modal-V2.fr-modal__title) {
  color: var(--blue-france-sun-113-625);
  max-width: 83.33333%;
  width: 83.33333%;
  margin-left: 16.66667%;
}

.visio-meeting-modal-title-illustration {
  max-width: 16.66667%;
  width: 16.66667%;
  position: absolute;
  top: 2rem;
}
</style>
