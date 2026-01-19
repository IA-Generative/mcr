<template>
  <DsfrFooter
    :logo-text="logoText"
    home-link="/"
  />
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const logoText = computed(() => [t('header.logo.text1'), t('header.logo.text2')]);
</script>

<style scoped></style>
