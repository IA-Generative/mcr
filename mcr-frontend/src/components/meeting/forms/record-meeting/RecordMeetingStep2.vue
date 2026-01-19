<template>
  <div>
    <DsfrAlert :title="$t('meeting.record-form.fields.notice-2.title')">
      <template #default>
        <div class="flex mt-2 gap-2 items-center">
          <span class="fr-icon-warning-line mr-2"></span>
          <p>{{ $t('meeting.record-form.fields.notice-2.warning') }}</p>
        </div>
      </template>
    </DsfrAlert>
  </div>

  <div class="mt-8 text-center">
    <DsfrButtonGroup
      inline-layout-when="md"
      align="right"
      reverse
    >
      <DsfrButton
        icon="ri-mic-line"
        @click="() => $emit('nextStep')"
      >
        {{ $t('meeting.record-form.actions.submit') }}
      </DsfrButton>
      <DsfrButton
        tertiary
        no-outline
        class="'max-sm:!hidden'"
        @click="() => $emit('cancel')"
      >
        {{ $t('common.cancel') }}
      </DsfrButton>
      <DsfrButton
        tertiary
        no-outline
        class="!mr-auto"
        @click="() => $emit('previousStep')"
      >
        {{ $t('meeting.record-form.actions.back') }}
      </DsfrButton>
    </DsfrButtonGroup>
  </div>
</template>

<script setup lang="ts">
defineEmits<{
  cancel: [];
  nextStep: [];
  previousStep: [];
}>();
</script>
