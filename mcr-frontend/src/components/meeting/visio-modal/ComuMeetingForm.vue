<template>
  <DsfrInputGroup
    class="m-0"
    :label="$t('meeting-v2.visio-form.comu.url')"
    :hint="$t('meeting-v2.visio-form.comu.url_hint')"
    label-visible
  />

  <div class="separator pt-2 pb-8">
    <span>{{ $t('common.or') }}</span>
  </div>

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
.separator {
  display: flex;
  align-items: center;
  text-align: center;
  color: #000;
  font-weight: 500;
}

.separator::before,
.separator::after {
  content: '';
  flex: 1;
  border-bottom: 1px solid #ddd;
}

.separator::before {
  margin-right: 10px;
}

.separator::after {
  margin-left: 10px;
}

:deep(.fr-input-group) {
  flex-grow: 1;
}
</style>
