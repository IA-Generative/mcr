<template>
  <form @submit.prevent>
    <div class="mt-3">
      <DsfrStepper
        :steps="[$t('meeting.record-form.steps.step-1'), $t('meeting.record-form.steps.step-2')]"
        :current-step="currentStep"
      />
      <RecordMeetingStep1
        v-if="currentStep === 1"
        @cancel="$emit('cancel')"
        @next-step="() => onNextStep()"
      />
      <RecordMeetingStep2
        v-else-if="currentStep === 2"
        @cancel="$emit('cancel')"
        @previous-step="() => onPreviousStep()"
        @next-step="() => onSubmit()"
      />
    </div>
  </form>
</template>

<script setup lang="ts">
import { useForm } from 'vee-validate';
import { toTypedSchema } from '@vee-validate/yup';
import { DsfrStepper } from '@gouvminint/vue-dsfr';
import { recordFieldsToMeetingDto, RecordMeetingSchema } from './record-meeting.schema';
import type { AddRecordMeetingDto } from '@/services/meetings/meetings.types';

const emit = defineEmits<{
  submit: [values: AddRecordMeetingDto];
  cancel: [];
}>();

const { handleSubmit } = useForm({
  validationSchema: toTypedSchema(RecordMeetingSchema),
  initialValues: { micId: 'default', name: '' },
  keepValuesOnUnmount: true,
});

const currentStep = ref(1);

function onNextStep() {
  currentStep.value++;
}

function onPreviousStep() {
  currentStep.value--;
}

const onSubmit = handleSubmit((values) => {
  emit('submit', recordFieldsToMeetingDto(values));
});
</script>

<style scoped>
:deep(h2, h3) {
  margin: var(--title-spacing);
}

:deep(.fr-stepper__details) {
  /* Hide the stepper next steps */
  display: none;
}
</style>
