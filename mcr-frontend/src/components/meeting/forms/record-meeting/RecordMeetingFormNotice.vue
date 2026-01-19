<template>
  <DsfrAlert
    :title="$t('meeting.record-form.fields.notice.title')"
    class="wrapper"
  >
    <template #default>
      <ul class="mcr-li">
        <i18n-t
          keypath="meeting.record-form.fields.notice.mic.text"
          tag="li"
        >
          <template #bold>
            <b>
              {{ $t('meeting.record-form.fields.notice.mic.bold') }}
            </b>
          </template>
        </i18n-t>
        <i18n-t
          keypath="meeting.record-form.fields.notice.noise.text"
          tag="li"
        >
          <template #bold>
            <b>
              {{ $t('meeting.record-form.fields.notice.noise.bold') }}
            </b>
          </template>
        </i18n-t>
        <i18n-t
          keypath="meeting.record-form.fields.notice.clarity.text"
          tag="li"
        >
          <template #bold>
            <b>
              {{ $t('meeting.record-form.fields.notice.clarity.bold') }}
            </b>
          </template>
        </i18n-t>
      </ul>
    </template>
  </DsfrAlert>
</template>

<style scoped>
ul.mcr-li li {
  --icon-size: 1.5rem;
  --dot-size: 1ex;
  --spacing: calc((var(--icon-size) - var(--dot-size)) * 0.5);
  list-style: disc;
  list-style-position: inside;
  padding-left: var(--spacing);
}

ul.mcr-li li::marker {
  margin-right: var(--spacing);
}
</style>
