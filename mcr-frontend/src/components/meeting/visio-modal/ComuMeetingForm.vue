<template>
  <div class="fr-grid-row fr-grid-row--gutters">
    <div class="fr-col-4">
      <DsfrRadioButtonSet
        v-model="comuConnectionMode"
        legend="Mode de connexion par"
        :options="[
          { value: 'idcode', name: 'idcode', label: 'identifiants' },
          { value: 'url', name: 'url', label: 'URL modérateur' },
        ]"
      />
    </div>
    <template v-if="comuConnectionMode == 'idcode'">
        <div class="fr-col-4 pt-2">
          <DsfrInput
            v-model="comuId"
            class="w-full flex-1"
            :label="$t('meeting-v2.visio-form.comu.meeting_id')"
            :error-message="comuIdError"
            label-visible
            :disabled="!isIdPasswordEnabled"
          />
        </div>
        <div class="fr-col-4 pt-2">
          <DsfrInputGroup
            v-model="comuPassword"
            class="w-full flex-1"
            :label="$t('meeting-v2.visio-form.comu.access_code')"
            :error-message="comuPasswordError"
            label-visible
            :disabled="!isIdPasswordEnabled"
          />
        </div>
    </template>
    <div 
    v-else
    class="fr-col-8 ">
      <DsfrInput
        v-model="comuUrl"
        class="m-0"
        :label="$t('meeting-v2.visio-form.comu.url')"
        :hint="$t('meeting-v2.visio-form.comu.url_hint')"
        :error-message="comuUrlError"
        label-visible
        :disabled="!isUrlEnabled"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useField } from 'vee-validate';

const { value: comuUrl, errorMessage: comuUrlError } = useField<string>('url');
const { value: comuPassword, errorMessage: comuPasswordError } =
  useField<string>('meeting_password');
const { value: comuId, errorMessage: comuIdError } = useField<string>('meeting_platform_id');

const isIdPasswordEnabled = computed(() => {
  return comuUrl.value === null || comuUrl.value === '';
});
const isUrlEnabled = computed(() => {
  return (
    (comuPassword.value === null || comuPassword.value === '') &&
    (comuId.value === null || comuId.value === '')
  );
});

const comuConnectionMode = ref<'idcode' | 'url'>('idcode');

</script>

<style scoped>
:deep(.fr-input-group) {
  flex-grow: 1;
  min-width: 50%;
}

:deep(.fr-label) {
  color: unset;
}

:deep(.fr-hint-text) {
  color: var(--text-mention-grey);
}
:deep(.fr-hint-text) {
  word-break: break-all; 
}
</style>
