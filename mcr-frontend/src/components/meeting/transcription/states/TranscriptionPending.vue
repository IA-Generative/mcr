<template>
  <div class="flex flex-col items-center gap-5">
    <DsfrAlert
      :title="$t('meeting.transcription.transcription-pending.title')"
      :description="$t('meeting.transcription.transcription-pending.description')"
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
