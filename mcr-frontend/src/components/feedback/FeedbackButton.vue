<template>
  <button
    type="button"
    class="trigger fr-btn fr-btn--primary fr-btn--md"
    aria-haspopup="dialog"
    @click="modal.open()"
  >
    <img
      :src="communityIcon"
      role="presentation"
      class="trigger-icon"
    />
    {{ t('feedback.button.label') }}
  </button>
</template>

<script setup lang="ts">
import communityIcon from '@dsfr-artwork/pictograms/leisure/community.svg?url';
import FeedbackModal from './FeedbackModal.vue';
import { t } from '@/plugins/i18n';
import { useModal } from 'vue-final-modal';

const modal = useModal({
  component: FeedbackModal,
});
</script>

<style scoped>
.trigger {
  position: fixed;
  z-index: 1000;
  bottom: 24px;
  right: 24px;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  border-radius: 24px;
}

.trigger-icon {
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  background-color: #fff;
  border-radius: 50%;
  padding: 2px;
}

@media (max-width: 550px) {
  .trigger {
    bottom: 16px;
    right: 16px;
  }
}
</style>
