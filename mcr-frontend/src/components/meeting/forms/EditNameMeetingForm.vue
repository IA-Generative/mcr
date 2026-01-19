<template>
  <form @submit.prevent="onSubmit">
    <div class="grid grid-cols-1 gap-4">
      <DsfrInputGroup
        v-model="name"
        required
        :error-message="errors.name"
        :label="$t('meeting.record-form.fields.name')"
        label-visible
        aria-required="true"
        v-bind="nameAttrs"
        wrapper-class="w-full"
        class="w-full"
      />
    </div>

    <div class="mt-8 text-center">
      <DsfrButtonGroup
        inline-layout-when="md"
        align="right"
        reverse
      >
        <DsfrButton
          :disabled="isDisabled"
          type="submit"
          >{{ $t('meeting.record-form.actions.update') }}</DsfrButton
        >
        <DsfrButton
          tertiary
          no-outline
          type="button"
          @click="emit('cancel')"
          >{{ $t('meeting.record-form.actions.cancel') }}</DsfrButton
        >
      </DsfrButtonGroup>
    </div>
  </form>
</template>

<script setup lang="ts">
import { useForm, useIsFormValid } from 'vee-validate';
import { toTypedSchema } from '@vee-validate/yup';
import type { UpdateMeetingDto } from '@/services/meetings/meetings.types';
import { EditRecordMeetingSchema } from '../meeting.schema';

const emit = defineEmits<{
  submit: [values: UpdateMeetingDto];
  cancel: [];
}>();

const props = defineProps<{
  loading?: boolean;
  initialValues?: UpdateMeetingDto;
}>();

const { defineField, errors, handleSubmit } = useForm({
  validationSchema: toTypedSchema(EditRecordMeetingSchema),
  initialValues: props.initialValues,
});

const isValid = useIsFormValid();

const isDisabled = computed(() => {
  return props.loading || !isValid.value;
});

const onSubmit = handleSubmit((values) => {
  emit('submit', values);
});

const [name, nameAttrs] = defineField('name');
</script>
