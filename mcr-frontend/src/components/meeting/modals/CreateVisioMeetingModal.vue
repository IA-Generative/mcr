<template>
  <BaseModal
    :modal-id="CREATE_MEETING_MODAL_ID"
    :title="''"
    size="lg"
    class="max-sm:p-4"
    :actions="[
      {
        label: $t('common.cancel'),
        secondary: true,
        onClick: () => close(),
      },
    ]"
  >
    <div>
      <img src="@dsfr-artwork/pictograms/digital/self-training.svg?url" />
      <h2
        id="modal-title"
        class="fr-modal__title"
      >
        {{ $t('meeting-v2.visio-form.title') }}
      </h2>
    </div>
  </BaseModal>
</template>

<script setup lang="ts">
import BaseModal from '@/components/core/BaseModal.vue';
import { useVfm } from 'vue-final-modal';

const CREATE_MEETING_MODAL_ID = 'meeting-visio-modal-V2';
const close = () => useVfm().close(CREATE_MEETING_MODAL_ID);
</script>

<style scoped>
:deep(.fr-modal__title) {
  color: var(--blue-france-sun-113-625);
}
</style>
