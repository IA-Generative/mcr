<template>
  <BaseModal
    :modal-id="VISIO_ADVICES_MODAL_ID"
    :title="''"
    size="lg"
    class="max-sm:p-4"
  >
    <div>
      <img src="@dsfr-artwork/pictograms/digital/self-training.svg?url" />
      <h2
        id="modal-title"
        class="fr-modal__title text-blue-france-sun"
      >
        {{ $t('meeting-v2.visio-recording.advices.modal.title') }}
      </h2>
      <h3 class="fr-h6 mb-1">
        {{ $t('meeting-v2.visio-recording.advices.modal.section-1.title') }}
      </h3>
      <ul class="list-disc pl-8 mb-6">
        <li>
          <i18n-t keypath="meeting-v2.visio-recording.advices.modal.section-1.advice-1.text">
            <template #bold>
              <strong>{{
                $t('meeting-v2.visio-recording.advices.modal.section-1.advice-1.bold')
              }}</strong>
            </template>
          </i18n-t>
        </li>
        <li>
          <i18n-t keypath="meeting-v2.visio-recording.advices.modal.section-1.advice-2.text">
            <template #bold>
              <strong>{{
                $t('meeting-v2.visio-recording.advices.modal.section-1.advice-2.bold')
              }}</strong>
            </template>
          </i18n-t>
        </li>
        <li>
          <i18n-t keypath="meeting-v2.visio-recording.advices.modal.section-1.advice-3.text">
            <template #bold>
              <strong>{{
                $t('meeting-v2.visio-recording.advices.modal.section-1.advice-3.bold')
              }}</strong>
            </template>
          </i18n-t>
        </li>
        <li>
          <i18n-t keypath="meeting-v2.visio-recording.advices.modal.section-1.advice-4.text">
            <template #bold>
              <strong>{{
                $t('meeting-v2.visio-recording.advices.modal.section-1.advice-4.bold')
              }}</strong>
            </template>
          </i18n-t>
        </li>
      </ul>
      <h3 class="fr-h6 mb-1">
        {{ $t('meeting-v2.visio-recording.advices.modal.section-2.title') }}
      </h3>
      <ul class="list-disc pl-8 mb-6">
        <li>
          <i18n-t keypath="meeting-v2.visio-recording.advices.modal.section-2.advice-1.text">
            <template #bold>
              <strong>{{
                $t('meeting-v2.visio-recording.advices.modal.section-2.advice-1.bold')
              }}</strong>
            </template>
          </i18n-t>
          <br />
          <span
            >→ {{ $t('meeting-v2.visio-recording.advices.modal.section-2.advice-1-detail') }}</span
          >
        </li>
      </ul>
      <DsfrCallout>
        <i18n-t keypath="meeting-v2.visio-recording.advices.modal.callout">
          <template #link>
            <a
              href="https://mirai.interieur.gouv.fr/outils-mirai/compte-rendu/bonnes-pratiques-fcr/"
              target="_blank"
              rel="noopener noreferrer"
              class="fr-link fr-link--icon-right fr-icon-external-link-line"
            >
              {{ $t('meeting-v2.visio-recording.advices.modal.callout-link') }}
            </a>
          </template>
        </i18n-t>
      </DsfrCallout>
    </div>
    <template #footer>
      <div class="flex w-full items-center justify-end border-t border-gray-300 pt-4">
        <DsfrButton
          :label="$t('meeting-v2.visio-recording.advices.modal.confirm')"
          icon="ri-check-line"
          @click="close"
        />
      </div>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import BaseModal from '@/components/core/BaseModal.vue';
import { useVfm } from 'vue-final-modal';

const VISIO_ADVICES_MODAL_ID = 'visio-advices-modal';
const close = () => useVfm().close(VISIO_ADVICES_MODAL_ID);
</script>
