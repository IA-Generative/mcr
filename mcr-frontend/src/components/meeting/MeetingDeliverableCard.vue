<template>
  <div class="deliverable-card">
    <h2 class="deliverable-card__title">{{ $t('meeting-v2.deliverable-card.title') }}</h2>
    <p class="deliverable-card__description">{{ $t('meeting-v2.deliverable-card.description') }}</p>

    <DsfrRadioButtonSet
      v-model="selectedType"
      name="deliverable-type"
      :options="radioOptions"
    />

    <DsfrButton
      icon="ri-refresh-line"
      :disabled="allGenerated"
      @click="generate"
    >
      {{ $t('meeting-v2.deliverable-card.generate-button') }}
    </DsfrButton>

    <div
      v-if="generatedDeliverables.length"
      class="deliverable-card__items"
    >
      <DeliverableItem
        v-for="item in generatedDeliverables"
        :key="item.id"
        :title="item.title"
        :status="item.status"
        :file-format="item.fileFormat"
        :file-size="item.fileSize"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import DeliverableItem from './DeliverableItem.vue';
import type { DeliverableStatus } from '@/services/deliverables/deliverables.types';
import { t } from '@/plugins/i18n';

interface MockDeliverable {
  id: number;
  type: string;
  title: string;
  status: DeliverableStatus;
  fileFormat: string;
  fileSize: string;
}

const selectedType = ref<string>('decision-text');
const generatedDeliverables = ref<MockDeliverable[]>([]);
let nextId = 1;

const generatedTypes = computed(() => new Set(generatedDeliverables.value.map((d) => d.type)));

const radioOptions = computed(() => [
  {
    label: t('meeting-v2.deliverable-card.type.decision-text.label'),
    hint: t('meeting-v2.deliverable-card.type.decision-text.hint'),
    value: 'decision-text',
    disabled: generatedTypes.value.has('decision-text'),
  },
  {
    label: t('meeting-v2.deliverable-card.type.decision-table.label'),
    hint: t('meeting-v2.deliverable-card.type.decision-table.hint'),
    value: 'decision-table',
    disabled: generatedTypes.value.has('decision-table'),
  },
]);

const allGenerated = computed(() => radioOptions.value.every((o) => o.disabled));

function generate(): void {
  const isText = selectedType.value === 'decision-text';
  generatedDeliverables.value.push({
    id: nextId++,
    type: selectedType.value,
    title: isText
      ? t('meeting-v2.deliverable-card.type.decision-text.title')
      : t('meeting-v2.deliverable-card.type.decision-table.title'),
    status: 'DONE',
    fileFormat: isText ? 'DOC' : 'PDF',
    fileSize: isText ? '42,5 Ko' : '61,88 Ko',
  });
}
</script>

<style scoped>
.deliverable-card {
  background-color: white;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  border-width: 1px;
  border-color: var(--grey-975-75-hover);
}

.deliverable-card__title {
  color: var(--blue-france-sun-113-625);
  font-weight: bold;
  font-size: 1.5rem;
}

.deliverable-card__description {
  color: var(--text-default-grey);
  margin: 0;
}

.deliverable-card__items {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
</style>
