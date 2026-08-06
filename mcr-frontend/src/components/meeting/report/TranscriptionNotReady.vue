<template>
  <div class="flex flex-col items-center justify-center px-6 py-24">
    <div class="mb-4 flex items-center justify-center">
      <img
        src="@dsfr-artwork/pictograms/system/warning.svg?url"
        role="presentation"
        class="h-22 w-22"
      />
    </div>

    <div class="text-center">
      <h3 class="mb-6 text-xl font-bold text-blue-france-sun">
        {{ $t('meeting.report.error.no-transcription.title') }}
      </h3>
      <p class="text-lg text-grey">
        {{ $t('meeting.report.error.no-transcription.description') }}
      </p>
    </div>
  </div>
</template>
