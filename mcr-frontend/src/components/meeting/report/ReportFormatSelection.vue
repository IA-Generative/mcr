<template>
  <div class="flex flex-col justify-center items-center">
    <div class="flex flex-col justify-center items-center gap-10 mb-5">
      <span class="text-body-grey">{{ $t('meeting.report.disclaimer.description') }}</span>
      <span class="text-base"> {{ $t('meeting.report.disclaimer.title') }}</span>
    </div>
    <div class="flex flex-col gap-10 justify-center items-center">
      <div class="flex gap-5">
        <DsfrButton
          secondary
          :class="{ active: choice === 'cr1' }"
          class="fr-tile shadow-none"
          @click="handleSelect('cr1')"
        >
          {{ $t('meeting.report.type.cr1') }}
        </DsfrButton>
        <DsfrButton
          secondary
          disabled
          :class="{ active: choice === 'cr2' }"
          class="fr-tile shadow-none"
          @click="handleSelect('cr2')"
        >
          {{ $t('meeting.report.type.cr2') }}
        </DsfrButton>
        <DsfrButton
          secondary
          disabled
          :class="{ active: choice === 'cr3' }"
          class="fr-tile shadow-none"
          @click="handleSelect('cr3')"
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
          {{ $t(props.actionLabelKey) }}
        </DsfrButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  actionLabelKey: string;
}>();
const choice = ref('cr1');

function handleSelect(value: string) {
  choice.value = value;
}

defineEmits<{
  onGenerate: [values: string];
}>();
</script>

<style scoped>
.active {
  box-shadow: 0 0.25rem 0 0px var(--border-action-high-blue-france);
}
</style>
