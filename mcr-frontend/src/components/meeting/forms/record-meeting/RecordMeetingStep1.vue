<template>
  <div class="grid grid-cols-1 gap-4">
    <RecordMeetingFormNotice />
    <DsfrInputGroup
      v-model="name"
      required
      :error-message="nameError"
      :label="$t('meeting.record-form.fields.name')"
      label-visible
      aria-required="true"
      wrapper-class="w-full"
      class="w-full"
    />

    <DsfrSelect
      v-model="micId"
      :label="$t('meeting.record-form.fields.devices')"
      :error-message="micIdError"
      border-bottom
      required
      :options="devices"
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
        @click="() => $emit('nextStep')"
      >
        {{ $t('meeting.record-form.actions.next') }}
      </DsfrButton>
      <DsfrButton
        tertiary
        no-outline
        @click="() => $emit('cancel')"
      >
        {{ $t('meeting.record-form.actions.cancel') }}
      </DsfrButton>
    </DsfrButtonGroup>
  </div>
</template>

<script setup lang="ts">
import { useField, useIsFormDirty, useIsFormValid } from 'vee-validate';
import { useRecorder } from '@/composables/use-recorder';

defineEmits<{
  cancel: [];
  nextStep: [];
}>();

const props = defineProps<{
  loading?: boolean;
}>();

const { value: name, errorMessage: nameError } = useField<string>('name');
const { value: micId, errorMessage: micIdError } = useField<string>('micId', undefined, {
  initialValue: 'default',
});
const isDirty = useIsFormDirty();
const isValid = useIsFormValid();

const isDisabled = computed(() => {
  return props.loading || !isDirty.value || !isValid.value;
});
const { getAudioInputDevices } = useRecorder();

const devices = ref<McrSelectOption[]>([]);

type McrSelectOption = {
  value: string;
  text: string;
};

async function loadDevices() {
  const devicesInfo = await getAudioInputDevices();
  devices.value = devicesInfo.map((device) => {
    return { value: device.deviceId, text: device.label };
  });
}

onMounted(loadDevices);
</script>
