<template>
  <BaseModal
    :modal-id="CREATE_MEETING_MODAL_ID"
    :title="$t('meetingV2.form.title')"
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
    <img src="/path_img" />
  </BaseModal>
</template>

<script setup lang="ts">
import BaseModal from '@/components/core/BaseModal.vue';
import { useVfm } from 'vue-final-modal';

const CREATE_MEETING_MODAL_ID = 'meeting-visio-modal-V2';
const close = () => useVfm().close(CREATE_MEETING_MODAL_ID);
</script>
