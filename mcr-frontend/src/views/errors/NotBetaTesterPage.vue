<template>
  <div class="flex h-full items-center justify-center py-10">
    <DsfrErrorPage
      :title="$t('not-tester.title')"
      subtitle=""
      :description="$t('not-tester.description')"
      help=""
    >
      <template #default>
        <i18n-t
          keypath="not-tester.help.text"
          tag="p"
        >
          <template #url>
            <a
              href="https://grist.numerique.gouv.fr/o/miraigrist/forms/uKvQErgDh2QHjtH7yzBd4k/106"
              target="_blank"
              >{{ $t('not-tester.help.text-url') }}</a
            >
          </template>
        </i18n-t>
      </template>
    </DsfrErrorPage>
  </div>
</template>
