<template>
  <BaseModal
    :modal-id="RECORDING_MEETING_ADVICES_MODAL_ID"
    :title="''"
    size="lg"
    class="max-sm:p-4"
  >
    <div>
      <img src="@dsfr-artwork/pictograms/leisure/podcast.svg?url" />
      <h2
        id="modal-title"
        class="fr-modal__title"
      >
        {{ $t('meeting-v2.recording.advices.modal.title') }}
      </h2>
      <h3 class="fr-h6 mb-1">{{ $t('meeting-v2.recording.advices.modal.section-1.title') }}</h3>
      <ul class="list-disc pl-8 mb-6">
        <li>
          <i18n-t keypath="meeting-v2.recording.advices.modal.section-1.advice-1.text">
            <template #bold>
              <strong>{{
                $t('meeting-v2.recording.advices.modal.section-1.advice-1.bold')
              }}</strong>
            </template>
          </i18n-t>
        </li>
        <li>
          <i18n-t keypath="meeting-v2.recording.advices.modal.section-1.advice-2.text">
            <template #bold>
              <strong>{{
                $t('meeting-v2.recording.advices.modal.section-1.advice-2.bold')
              }}</strong>
            </template>
          </i18n-t>
        </li>
        <li>
          <i18n-t keypath="meeting-v2.recording.advices.modal.section-1.advice-3.text">
            <template #bold>
              <strong>{{
                $t('meeting-v2.recording.advices.modal.section-1.advice-3.bold')
              }}</strong>
            </template>
          </i18n-t>
        </li>
      </ul>
      <h3 class="fr-h6 mb-1">{{ $t('meeting-v2.recording.advices.modal.section-2.title') }}</h3>
      <ul class="list-disc pl-8">
        <li>
          <i18n-t keypath="meeting-v2.recording.advices.modal.section-2.advice-1.text">
            <template #bold>
              <strong>{{
                $t('meeting-v2.recording.advices.modal.section-2.advice-1.bold')
              }}</strong>
            </template>
          </i18n-t>
        </li>
        <li>
          <i18n-t keypath="meeting-v2.recording.advices.modal.section-2.advice-2.text">
            <template #bold>
              <strong>{{
                $t('meeting-v2.recording.advices.modal.section-2.advice-2.bold')
              }}</strong>
            </template>
          </i18n-t>
        </li>
      </ul>
    </div>
    <template #footer>
      <div class="flex w-full items-center justify-between border-t border-gray-300 pt-4">
        <a
          href="https://mirai.interieur.gouv.fr/conditions-generales-dutilisation/"
          target="_blank"
          rel="noopener noreferrer"
          class="fr-link fr-link--sm"
        >
          {{ $t('meeting-v2.recording.advices.modal.cgu') }}
        </a>
        <DsfrButton
          :label="$t('meeting-v2.recording.advices.modal.confirm')"
          @click="close"
        />
      </div>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import BaseModal from '@/components/core/BaseModal.vue';
import { useVfm } from 'vue-final-modal';

const RECORDING_MEETING_ADVICES_MODAL_ID = 'recording-meeting-advices-modal';
const close = () => useVfm().close(RECORDING_MEETING_ADVICES_MODAL_ID);
</script>

<style scoped>
:deep(.fr-modal__title) {
  color: var(--blue-france-sun-113-625);
}
</style>
