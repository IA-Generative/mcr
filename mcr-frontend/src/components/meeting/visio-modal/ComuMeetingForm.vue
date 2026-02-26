<template>
  <DsfrInputGroup
    v-model="comuUrl"
    class="m-0"
    :label="$t('meeting-v2.visio-form.comu.url')"
    :hint="$t('meeting-v2.visio-form.comu.url_hint')"
    :error-message="comuUrlError"
    label-visible
  />

  <VisioConnectionSeparator />

  <div class="flex flex-row gap-x-6 pb-4">
    <DsfrInputGroup
      v-model="comuAccessCode"
      class="w-full flex-1"
      :label="$t('meeting-v2.visio-form.comu.access_code')"
      label-visible
    />

    <DsfrInputGroup
      v-model="comuId"
      class="w-full flex-1"
      :label="$t('meeting-v2.visio-form.comu.meeting_id')"
      :error-message="comuIdError"
      label-visible
    />
  </div>

  <hr />

  <div class="flex justify-end">
    <DsfrButton
      :label="$t('meeting-v2.visio-form.submit')"
      icon="fr-icon-play-circle-fill"
      :disabled="!isSubmitEnabled"
      @click="handleSubmit()"
    />
  </div>
</template>

<script setup lang="ts">
import { t } from '@/plugins/i18n';
import { comuPrivateUrlValidator } from '../meeting.schema';
import VisioConnectionSeparator from './VisioConnectionSeparator.vue';
import type { AddOnlineMeetingDto } from '@/services/meetings/meetings.types';

const props = defineProps<{
  title: string;
}>();

const comuUrl = ref<string>('');
const comuUrlError = computed(() => {
  if (!comuUrl.value) return '';
  if (!comuPrivateUrlValidator.test(comuUrl.value)) {
    return t('meeting-v2.visio-form.comu.url_error');
  }
  return '';
});

const comuId = ref<string>('');
const comuIdError = computed(() => {
  if (!comuId.value) return '';
  if (!RegExp(/^[0-9]+$/).test(comuId.value)) {
    return t('meeting-v2.visio-form.comu.meeting_id_error');
  }
  return '';
});

const comuAccessCode = ref<string>('');

const isSubmitEnabled = computed(() => {
  return (
    props.title !== '' &&
    (comuPrivateUrlValidator.test(comuUrl.value) ||
      (comuAccessCode.value !== '' && comuId.value !== ''))
  );
});

const emit = defineEmits<{
  submit: [visioUrl: AddOnlineMeetingDto];
  cancel: [];
}>();

function handleSubmit() {
  const dto: AddOnlineMeetingDto = {
    name: props.title,
    name_platform: 'COMU',
    url: comuUrl.value ?? undefined,
    meeting_platform_id: comuId.value ?? undefined,
    meeting_password: comuAccessCode.value ?? undefined,
    creation_date: new Date().toISOString(),
  };
  emit('submit', dto);
}
</script>

<style scoped>
:deep(.fr-input-group) {
  flex-grow: 1;
  min-width: 50%;
}
</style>
