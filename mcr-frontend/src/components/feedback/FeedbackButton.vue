<template>
  <button
    type="button"
    class="trigger fr-btn fr-btn--primary fr-btn--md"
    :class="{ 'trigger--compact': compact }"
    aria-haspopup="dialog"
    @click="modal.open()"
  >
    <img
      :src="communityIcon"
      role="presentation"
      class="trigger-icon"
    />
    <span class="trigger-label">{{ t('feedback.button.label') }}</span>
  </button>
</template>

<script setup lang="ts">
import communityIcon from '@dsfr-artwork/pictograms/leisure/community.svg?url';
import FeedbackModal from './FeedbackModal.vue';
import { t } from '@/plugins/i18n';
import { useModal } from 'vue-final-modal';

defineProps<{ compact?: boolean }>();

const modal = useModal({
  component: FeedbackModal,
});
</script>

<style scoped>
.trigger {
  position: fixed;
  z-index: 1000;
  bottom: var(--sticky-corner-margin);
  right: var(--sticky-corner-margin);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 24px;
  transition:
    right 0.3s ease,
    border-radius 0.3s ease,
    padding 0.3s ease,
    width 0.3s ease;
}

.trigger-icon {
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  background-color: #fff;
  border-radius: 50%;
  padding: 2px;
}

.trigger-label {
  max-width: 12rem;
  overflow: hidden;
  white-space: nowrap;
  margin-left: 0.5rem;
  transition:
    max-width 0.3s ease,
    margin-left 0.3s ease,
    opacity 0.3s ease;
}

.trigger--compact {
  right: calc(var(--sticky-corner-margin) + var(--import-sticky-width) + var(--sticky-corner-gap));
  border-radius: 50%;
  padding: 8px;
  width: var(--feedback-compact-size);
  height: var(--feedback-compact-size);
  min-height: 0;
}

.trigger--compact .trigger-label {
  max-width: 0;
  margin-left: 0;
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .trigger,
  .trigger-label {
    transition: none;
  }
}
</style>
