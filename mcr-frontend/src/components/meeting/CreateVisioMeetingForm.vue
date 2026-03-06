<template>
  <div class="text-xl font-semibold pb-4">{{ $t('meeting-v2.visio-form.parameters') }}</div>
  <DsfrInputGroup
    v-model="meetingTitle"
    :label="$t('meeting-v2.visio-form.meeting-title.title')"
    :hint="$t('meeting-v2.visio-form.meeting-title.example')"
    v-bind="meetingTitleAttrs"
    label-visible
  />
  <div class="pb-8">
    <span class="pb-2">
      {{ $t('meeting-v2.visio-form.visio-tools') }}
    </span>
    <DsfrSelect
      v-model="selectedPlatform"
      :options="meetingPlatformOptions"
      class="w-2/5"
    />
  </div>

  <div
    v-if="selectedPlatform !== null"
    class="pb-4"
  >
    <div class="text-xl font-semibold pb-2">
      {{ $t('meeting-v2.visio-form.connection.title') }}
    </div>

    <DsfrNotice>
      <template #desc>
        <div class="flex flex-row items-center">
          <span
            class="fr-icon-info-fill fr-icon--sm pr-1"
            aria-hidden="true"
          ></span>
          <i18n-t
            class="text-xs"
            keypath="meeting-v2.visio-form.connection.advice"
            tag="p"
          >
            <template #link>
              <a
                :href="URL_GOOD_PRACTICES"
                target="_blank"
              >
                {{ $t('meeting-v2.visio-form.connection.link') }}
              </a>
            </template>
          </i18n-t>
        </div>
      </template>
    </DsfrNotice>
  </div>

  <component :is="currentVisioToolComponent" />

  <hr />

  <div class="flex justify-end">
    <DsfrButton
      :label="$t('meeting-v2.visio-form.submit')"
      icon="fr-icon-play-circle-fill"
      :disabled="!isFormValid"
      @click="onSubmit()"
    />
  </div>
</template>

<script setup lang="ts">
import {
  OnlineMeetingPlatforms,
  type AddOnlineMeetingDto,
} from '@/services/meetings/meetings.types';
import ComuMeetingForm from './visio-modal/ComuMeetingForm.vue';
import WebconfMeetingForm from './visio-modal/WebconfMeetingForm.vue';
import WebinaireMeetingForm from './visio-modal/WebinaireMeetingForm.vue';
import VisioMeetingForm from './visio-modal/VisioMeetingForm.vue';
import { useForm, useIsFormValid } from 'vee-validate';
import { toTypedSchema } from '@vee-validate/yup';
import { visioMeetingFieldsToVisioMeetingDto, VisioMeetingSchema } from './meeting.schema';

const platformLabels: Record<OnlineMeetingPlatforms, string> = {
  COMU: 'COMU',
  WEBINAIRE: "Webinaire de l'État",
  WEBCONF: 'Webconf',
  VISIO: 'Visio',
};

const { defineField, handleSubmit } = useForm({
  validationSchema: toTypedSchema(VisioMeetingSchema),
});

const [meetingTitle, meetingTitleAttrs] = defineField('name');

const meetingPlatformOptions = OnlineMeetingPlatforms.map((platform) => ({
  value: platform,
  text: platformLabels[platform],
}));
const selectedPlatform = ref<OnlineMeetingPlatforms | null>(null);

const URL_GOOD_PRACTICES =
  'https://mirai.interieur.gouv.fr/outils-mirai/compte-rendu/bonnes-pratiques-fcr/';

const currentVisioToolComponent = computed(() => getVisioToolComponent(selectedPlatform));

function getVisioToolComponent(selectedPlatform: Ref<OnlineMeetingPlatforms | null>) {
  switch (selectedPlatform.value) {
    case 'COMU':
      return ComuMeetingForm;
    case 'VISIO':
      return VisioMeetingForm;
    case 'WEBCONF':
      return WebconfMeetingForm;
    case 'WEBINAIRE':
      return WebinaireMeetingForm;
    default:
      return null;
  }
}

const emit = defineEmits<{
  submit: [values: AddOnlineMeetingDto];
  cancel: [];
}>();

const isFormValid = useIsFormValid();

const onSubmit = handleSubmit((values) => {
  emit('submit', visioMeetingFieldsToVisioMeetingDto(values));
});
</script>

<style scoped>
:deep() div.fr-notice__body > p {
  display: flex;
  flex-direction: row;
  align-items: center;
}

:deep(.fr-container) {
  padding: 0;
}

:deep(.fr-notice) {
  background-color: transparent;
  padding: 0;
}

:deep(.fr-notice__title:before) {
  display: none;
}

:deep(a[target='_blank']::after) {
  display: none !important; /* enlève l'icône à droite */
}
</style>
