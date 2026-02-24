<template>
  <DsfrInputGroup
    class="m-0"
    :label="$t('meeting-v2.visio-form.comu.url')"
    :hint="$t('meeting-v2.visio-form.comu.url_hint')"
    label-visible
  />

  <div class="flex flex-row gap-x-6">
    <DsfrInputGroup
      class="w-full flex-1"
      :label="$t('meeting-v2.visio-form.comu.access_code')"
      label-visible
    />

    <DsfrInputGroup
      class="w-full flex-1"
      :label="$t('meeting-v2.visio-form.comu.meeting_id')"
      label-visible
    />
  </div>

</template>

<style scoped>
:deep(.fr-input-group) {
  flex-grow: 1;
}
</style>
