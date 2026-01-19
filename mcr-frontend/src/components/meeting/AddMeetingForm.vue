<template>
  <form @submit.prevent="onSubmit">
    <div class="grid grid-cols-1 gap-10">
      <DsfrToggleSwitch
        v-model="addWithUrl"
        :label="$t('meeting.form.add-with-url')"
        no-text
      ></DsfrToggleSwitch>

      <div v-if="addWithUrl">
        <DsfrInputGroup
          v-model="url"
          required
          :error-message="errors.url"
          :label="$t('meeting.form.fields.url.label')"
          label-visible
          aria-required="true"
          v-bind="urlAttrs"
          wrapper-class="w-full"
          class="w-full"
          @update:model-value="(value) => validateUrlAndLookup(value)"
        />
      </div>

      <div
        v-else
        class="grid grid-cols-2 gap-5 max-sm:grid-cols-1"
      >
        <DsfrInputGroup
          v-model="externalMeetingId"
          required
          :error-message="errors.meeting_platform_id"
          :label="$t('meeting.form.fields.external-id')"
          label-visible
          aria-required="true"
          v-bind="externalMeetingIdAttrs"
          wrapper-class="w-full"
          class="w-full"
        />
        <DsfrInputGroup
          v-model="externalMeetingPassword"
          required
          :error-message="errors.meeting_password"
          :label="$t('meeting.form.fields.external-password')"
          label-visible
          aria-required="true"
          v-bind="externalMeetingPasswordAttrs"
          wrapper-class="w-full"
          class="w-full"
        />
      </div>

      <DsfrInputGroup
        v-model="name"
        required
        :error-message="errors.name"
        :label="$t('meeting.form.fields.name')"
        label-visible
        aria-required="true"
        v-bind="nameAttrs"
        wrapper-class="w-full"
        class="w-full"
      />
      <div class="mt-8 text-center">
        <slot
          name="actions"
          :disabled="btnDisabled"
        >
          <DsfrButtonGroup
            inline-layout-when="md"
            align="right"
            reverse
          >
            <DsfrButton
              :disabled="btnDisabled"
              type="submit"
              ><VIcon
                name="ri-add-line"
                class="mr-2"
              />
              {{ $t('meeting.form.submit') }}
            </DsfrButton>
            <DsfrButton
              tertiary
              no-outline
              type="button"
              @click="emit('cancel')"
              >{{ $t('common.cancel') }}</DsfrButton
            >
          </DsfrButtonGroup>
        </slot>
      </div>
    </div>
  </form>
</template>

<script setup lang="ts">
import { useForm, useIsFormValid } from 'vee-validate';
import { toTypedSchema } from '@vee-validate/yup';
import {
  AddMeetingSchema,
  comuPrivateUrlValidator,
  meetingFieldsToMeetingDto,
  webconfUrlValidator,
} from './meeting.schema';
import {
  type AddOnlineMeetingDto,
  type UpdateOnlineMeetingDto,
} from '@/services/meetings/meetings.types';
import { parseComuUrl } from '@/services/lookup/lookup.service';
import { useI18n } from 'vue-i18n';
import type { Nullable } from '@/utils/types';
import { parseWebconfUrl } from '@/utils/meeting';

import { useMeetings } from '@/services/meetings/use-meeting';

const { t } = useI18n();

const emit = defineEmits<{
  submit: [values: AddOnlineMeetingDto];
  cancel: [];
}>();

const props = defineProps<{
  loading?: boolean;
  initialValues?: UpdateOnlineMeetingDto;
}>();

const addWithUrl = ref(!props.initialValues?.meeting_platform_id);

const initialValuesWithDefaults = props.initialValues;
const { defineField, errors, handleSubmit, setValues, setErrors } = useForm({
  validationSchema: toTypedSchema(AddMeetingSchema),
  initialValues: initialValuesWithDefaults,
});

const isValid = useIsFormValid();

const btnDisabled = computed(() => props.loading || !isValid);

const onSubmit = handleSubmit((values) => {
  const dto = meetingFieldsToMeetingDto(values);
  emit('submit', dto);
});

const [name, nameAttrs] = defineField('name');
const [url, urlAttrs] = defineField('url');
const [externalMeetingPassword, externalMeetingPasswordAttrs] = defineField('meeting_password');
const [externalMeetingId, externalMeetingIdAttrs] = defineField('meeting_platform_id');

const { lookupMeetingUrlMutation } = useMeetings();
const { mutate: lookupMeetingUrlAndSetName } = lookupMeetingUrlMutation({
  onSuccess: async (data) => {
    setValues({
      name: data.name,
    });
  },
  onError: () => {
    setErrors({
      url: t('meeting.form.errors.url.not-found'),
    });
  },
});

function isValidComuUrl(url?: Nullable<string>): url is string {
  return url !== null && url !== undefined && comuPrivateUrlValidator.test(url);
}

function isValidWebconfUrl(url?: Nullable<string>): url is string {
  return url !== null && url !== undefined && webconfUrlValidator.test(url);
}

function validateUrlAndLookup(url?: Nullable<string>) {
  if (isValidComuUrl(url)) {
    lookupMeetingUrlAndSetName(parseComuUrl(url));
  } else if (isValidWebconfUrl(url)) {
    const meetingName = parseWebconfUrl(url);
    if (meetingName) {
      setValues({ name: meetingName });
    }
  }
}
</script>

<style scoped>
/* Remove bottom margin from input groups in horizontal grids */
:not(.grid-cols-1) > .fr-input-group {
  margin-bottom: 0;
}
</style>
