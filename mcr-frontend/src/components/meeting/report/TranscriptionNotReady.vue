<template>
  <div class="flex flex-col items-center justify-center px-6 py-24">
    <div class="flex justify-center items-center mb-4">
      <img
        src="@dsfr-artwork/pictograms/system/warning.svg?url"
        role="presentation"
        class="w-22 h-22"
      />
    </div>

    <div class="text-center">
      <h3 class="text-xl font-bold mb-6 text-[var(--blue-france-sun-113-625)]">
        {{ $t('meeting.report.error.no-transcription.title') }}
      </h3>
      <p class="text-gray-700 text-lg">
        {{ $t('meeting.report.error.no-transcription.description') }}
      </p>
    </div>
  </div>
</template>
