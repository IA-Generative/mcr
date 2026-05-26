<template>
  <BaseModal
    :modal-id="MODAL_ID"
    :title="''"
    size="lg"
    no-actions
    disable-close-on-outside-click
  >
    <div class="flex flex-col gap-6">
      <div class="flex flex-col gap-2">
        <h2
          id="modal-title"
          class="fr-modal__title text-blue-france-sun"
        >
          {{ $t('meeting-v2.custom-report-modal.title') }}
        </h2>
        <p class="text-[var(--text-default-grey)] m-0">
          {{ $t('meeting-v2.custom-report-modal.description') }}
        </p>
      </div>

      <div class="flex flex-col gap-1">
        <label
          for="custom-report-prompt"
          class="text-xs font-bold text-grey-mention"
        >
          {{ $t('meeting-v2.custom-report-modal.prompt-label').toUpperCase() }}
        </label>
        <textarea
          id="custom-report-prompt"
          v-model="prompt"
          class="fr-input overflow-y-auto resize-y"
          rows="5"
          :placeholder="$t('meeting-v2.custom-report-modal.prompt-placeholder')"
        />
      </div>

      <div class="flex flex-col gap-2">
        <span class="text-xs font-bold text-grey-mention">
          {{ $t('meeting-v2.custom-report-modal.suggestions-label').toUpperCase() }}
        </span>
        <div class="grid grid-cols-3 gap-2">
          <DsfrTile
            v-for="suggestion in suggestions"
            :key="suggestion.key"
            :title="suggestion.title"
            :description="suggestion.description"
            :img-src="suggestion.imgSrc"
            small
            horizontal
            class="cursor-pointer"
            @click="handleSuggestionClick(suggestion)"
          />
        </div>
      </div>
    </div>

    <template #footer>
      <div class="flex w-full justify-between gap-2">
        <DsfrButton
          tertiary
          no-outline
          @click="handleCancel"
        >
          {{ $t('meeting-v2.custom-report-modal.cancel-button') }}
        </DsfrButton>
        <DsfrButton
          icon="ri-refresh-line"
          :disabled="isGenerateDisabled"
          @click="handleGenerate"
        >
          {{ $t('meeting-v2.custom-report-modal.generate-button') }}
        </DsfrButton>
      </div>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import BaseModal from '@/components/core/BaseModal.vue';
import type { MessageSchema } from '@/plugins/i18n';
import { useVfm } from 'vue-final-modal';
import { useI18n } from 'vue-i18n';

import documentSvg from '@dsfr-artwork/pictograms/document/document.svg?url';
import conclusionSvg from '@dsfr-artwork/pictograms/document/conclusion.svg?url';
import dataVisualizationSvg from '@dsfr-artwork/pictograms/digital/data-visualization.svg?url';
import communitySvg from '@dsfr-artwork/pictograms/leisure/community.svg?url';

const MODAL_ID = 'custom-report-modal';

const props = defineProps<{
  initialPrompt: string;
  generateBlockedByPending: boolean;
}>();

const emit = defineEmits<{
  generate: [prompt: string];
  updatePrompt: [value: string];
}>();

const { t } = useI18n();

const prompt = ref(props.initialPrompt);

const isGenerateDisabled = computed(
  () => prompt.value.trim().length === 0 || props.generateBlockedByPending,
);

type SuggestionKey = keyof MessageSchema['meeting-v2']['custom-report-modal']['suggestions'];

type Suggestion = {
  key: SuggestionKey;
  title: string;
  description: string;
  prompt: string;
  imgSrc: string;
};

const SUGGESTION_IMG_MAP: Record<SuggestionKey, string> = {
  'quick-report': documentSvg,
  'action-plan': conclusionSvg,
  'structured-roundtable': communitySvg,
  'executive-summary': dataVisualizationSvg,
};

const SUGGESTION_KEYS = Object.keys(SUGGESTION_IMG_MAP) as SuggestionKey[];

const suggestions = computed<Suggestion[]>(() =>
  SUGGESTION_KEYS.map((key) => {
    const promptText = t(`meeting-v2.custom-report-modal.suggestions.${key}.prompt`);
    return {
      key,
      title: t(`meeting-v2.custom-report-modal.suggestions.${key}.title`),
      description: promptText,
      prompt: promptText,
      imgSrc: SUGGESTION_IMG_MAP[key],
    };
  }),
);

function handleSuggestionClick(suggestion: Suggestion) {
  prompt.value = suggestion.prompt;
}

function close() {
  useVfm().close(MODAL_ID);
}

onBeforeUnmount(() => {
  emit('updatePrompt', prompt.value);
});

function handleCancel() {
  close();
}

function handleGenerate() {
  emit('generate', prompt.value);
  close();
}
</script>

<style scoped>
:deep(.fr-modal__title) {
  color: var(--blue-france-sun-113-625);
}

:deep(.fr-tile) {
  padding: 0.75rem;
  min-height: 0;
  height: 8rem;
}

:deep(.fr-tile__link::after) {
  display: none;
}

:deep(.fr-tile__body) {
  padding: 0;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

:deep(.fr-tile__content) {
  padding: 0;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

:deep(.fr-tile__img) {
  width: 2.5rem;
  height: 2.5rem;
  margin-right: 0.75rem;
}

:deep(.fr-tile__img img) {
  max-width: 100%;
  max-height: 100%;
}

:deep(.fr-tile__title) {
  font-size: 0.875rem;
  margin: 0;
  flex: 0 0 auto;
}

:deep(.fr-tile__desc) {
  font-size: 0.75rem;
  margin: 0;
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}
</style>
