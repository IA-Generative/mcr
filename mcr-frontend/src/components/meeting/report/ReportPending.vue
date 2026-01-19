<template>
  <div class="flex flex-col items-center gap-5 py-24">
    <DsfrAlert
      :title="$t('meeting.report.report-pending.title')"
      :description="$t('meeting.report.report-pending.description')"
    />
  </div>
</template>

<style>
.fr-notice__title {
  display: block;
  margin-bottom: 0.5em; /* space below title */
}

.fr-notice__desc {
  display: block;
}
</style>
