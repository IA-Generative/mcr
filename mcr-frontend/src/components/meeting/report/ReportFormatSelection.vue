<template>
  <div class="flex flex-col justify-center items-center">
    <div class="flex flex-col justify-center items-center gap-10 mb-5">
      <span class="text-grey-625">{{ $t('meeting.report.disclaimer.description') }}</span>
      <span class="text-base"> {{ $t('meeting.report.disclaimer.title') }}</span>
    </div>
    <div class="flex flex-col gap-10 justify-center items-center">
      <div class="flex gap-5">
        <DsfrButton
          secondary
          :class="{ active: choice === 'DECISION_RECORD' }"
          class="fr-tile shadow-none"
          @click="handleSelect('DECISION_RECORD')"
        >
          {{ $t('meeting.report.type.cr1') }}
        </DsfrButton>
        <DsfrButton
          secondary
          :class="{ active: choice === 'DETAILED_SYNTHESIS' }"
          class="fr-tile shadow-none"
          @click="handleSelect('DETAILED_SYNTHESIS')"
        >
          {{ $t('meeting.report.type.cr2') }}
        </DsfrButton>
        <DsfrButton
          secondary
          disabled
          class="fr-tile shadow-none"
        >
          {{ $t('meeting.report.type.cr3') }}
        </DsfrButton>
      </div>
      <div class="flex flex-col justify-center items-center gap-5">
        <DsfrButton
          type="button"
          :disabled="!choice"
          @click="$emit('onGenerate', choice)"
        >
          {{ $t('meeting.report.generate') }}
        </DsfrButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ReportType } from '@/services/meetings/meetings.types';

const choice = ref<ReportType>('DECISION_RECORD');

function handleSelect(value: ReportType) {
  choice.value = value;
}

defineEmits<{
  onGenerate: [value: ReportType];
}>();
</script>

<style scoped>
.active {
  box-shadow: 0 0.25rem 0 0px var(--border-action-high-blue-france);
}
</style>
