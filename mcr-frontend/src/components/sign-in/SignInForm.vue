<template>
  <form @submit.prevent="onSubmit">
    <DsfrInputGroup
      v-model="username"
      :error-message="errors.username"
      placeholder="dupont@gmail.com"
      :label="$t('sign-in.username')"
      label-visible
      aria-required="true"
      v-bind="usernameAttrs"
      type="email"
      autocomplete="email"
      class="w-full"
      wrapper-class="w-full"
    />

    <DsfrInputGroup
      v-model="password"
      :error-message="errors.password"
      :label="$t('sign-in.password')"
      label-visible
      aria-required="true"
      v-bind="passwordAttrs"
      type="password"
      wrapper-class="w-full"
      class="w-full"
    />
    <div class="text-center">
      <DsfrButton
        :disabled="loading || !isValid"
        type="submit"
        >{{ $t('sign-in.connect') }}</DsfrButton
      >
    </div>
  </form>
</template>

<script setup lang="ts">
import { useForm, useIsFormValid } from 'vee-validate';
import { SignInSchema, type SignInField } from './sign-in.schema';
import { toTypedSchema } from '@vee-validate/yup';

const emit = defineEmits<{
  onSubmit: [values: SignInField];
}>();

defineProps<{
  loading?: boolean;
}>();

const { defineField, errors, handleSubmit } = useForm({
  validationSchema: toTypedSchema(SignInSchema),
});

const isValid = useIsFormValid();

const onSubmit = handleSubmit((values) => emit('onSubmit', values));

const [username, usernameAttrs] = defineField('username');
const [password, passwordAttrs] = defineField('password');
</script>

<style scoped></style>
