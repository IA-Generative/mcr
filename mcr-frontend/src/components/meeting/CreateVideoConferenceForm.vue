<template>
  <DsfrNotice
    type="info"
    title="Pour localiser votre URL ou vos identifiants modérateur,"
  >
    <template #desc>
      <a
      class="fr-notice__link"
      :href="URL_GOOD_PRACTICES"
      target="_blank"
      rel="noopener external">
      consulter cet article
    </a>
    </template>
  </DsfrNotice>
  <div class="pt-2 pb-4">
      <div class="fr-grid-row fr-grid-row--gutters">
        <div class="fr-col-8">
          <DsfrInput
            v-model="meetingTitle"
            :label="$t('meeting-v2.visio-form.meeting-title.title')"
            v-bind="meetingTitleAttrs"
            label-visible
          />
        </div>
        <div class="fr-col-4 flex items-end">
          <DsfrSelect
            v-model="selectedPlatform"
            :label="$t('meeting-v2.visio-form.visio-tools')"
            :options="meetingPlatformOptions"
            default-unselected-text="Sélectionner un outil"
          />
        </div>
      </div>
  </div>
  <div
    v-if="selectedPlatform !== null"
  >
    <component 
      :is="currentVisioToolComponent" 
    />
  </div> 

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
import { useForm, useFormErrors, useFormValues, useIsFormValid } from 'vee-validate';
import { toTypedSchema } from '@vee-validate/yup';
import {
  comuPrivateUrlValidator,
  visioMeetingFieldsToVisioMeetingDto,
  VisioMeetingSchema,
} from './meeting.schema.ts';
import { useMeetings } from '@/services/meetings/use-meeting';
import { parseComuUrl } from '@/services/lookup/lookup.service';
import { useI18n } from 'vue-i18n';

import WebexMeetingForm from './visio-modal/WebexMeetingForm.vue';
import { useFeatureFlag } from '@/composables/use-feature-flag';

const isWebexEnabled = useFeatureFlag('webex');
import useToaster from '@/composables/use-toaster';

const { t } = useI18n();
const toaster = useToaster();

const platformLabels: Record<OnlineMeetingPlatforms, string> = {
  COMU: 'COMU',
  WEBCONF: 'Webconf',
  WEBEX: 'Webex',
  WEBINAIRE: "Webinaire de l'État",
  VISIO: 'Visio',
};

const { defineField, handleSubmit } = useForm({
  validationSchema: toTypedSchema(VisioMeetingSchema),
});

const [meetingTitle, meetingTitleAttrs] = defineField('name');
const formValues = useFormValues();

const { lookupMeetingUrlMutation, lookupMeetingByPasscodeMutation } = useMeetings();

const formErrors = useFormErrors();

const onLookupError = () => {
  toaster.addMessage({
    description: t('meeting.form.errors.lookup-warning'),
    type: 'warning',
  });
};

const { mutate: lookupByUrl } = lookupMeetingUrlMutation({
  onError: onLookupError,
});

const { mutate: lookupByPasscode } = lookupMeetingByPasscodeMutation({
  onError: onLookupError,
});

watch(
  () => formValues.value.url,
  (newUrl) => {
    if (newUrl && comuPrivateUrlValidator.test(newUrl)) {
      lookupByUrl(parseComuUrl(newUrl));
    }
  },
);

function hasNoFieldErrors(...fields: string[]) {
  return fields.every((field) => !formErrors.value[field]);
}

watch(
  () => [formValues.value.meeting_platform_id, formValues.value.meeting_password],
  ([newId, newPassword]) => {
    if (
      selectedPlatform.value === 'COMU' &&
      newId &&
      newPassword &&
      hasNoFieldErrors('meeting_platform_id', 'meeting_password')
    ) {
      lookupByPasscode({ comu_meeting_id: newId, passcode: newPassword });
    }
  },
);

const meetingPlatformOptions = OnlineMeetingPlatforms.filter(
  (platform) => platform !== 'WEBEX' || isWebexEnabled.value,
).map((platform) => ({
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
    case 'WEBCONF':
      return WebconfMeetingForm;
    case 'WEBEX':
      if (isWebexEnabled.value) {
        return WebexMeetingForm;
      }
      return null;
    case 'WEBINAIRE':
      return WebinaireMeetingForm;
    case 'VISIO':
      return VisioMeetingForm;
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


:deep(.fr-notice) {
  display: flex;
  flex-direction: column;
}

</style>
