<template>
  <DsfrHeader
    :service-title="$t('header.app.name')"
    :service-description="$t('header.app.description')"
    :logo-text
    :quick-links
    :show-beta="true"
  >
    <template #before-quick-links>
      <DsfrDropdown
        :main-button="{
          label: $t('header.links.mirai-services.main-button'),
          icon: 'fr-icon-grid-fill',
          size: 'sm',
        }"
        class="max-sm:self-end"
        :buttons="[
          {
            label: $t('header.links.mirai-services.portal'),
            onClick: () => redirectTo('https://mirai.interieur.gouv.fr/'),
          },
          {
            label: $t('header.links.mirai-services.chat'),
            onClick: () => redirectTo('https://chat.mirai.interieur.gouv.fr/'),
          },
          {
            label: $t('header.links.mirai-services.resumer'),
            onClick: () => redirectTo('https://resume.mirai.interieur.gouv.fr/'),
          },
          {
            label: $t('header.links.mirai-services.ocr'),
            onClick: () => redirectTo('https://ocr.mirai.interieur.gouv.fr/'),
          },
        ]"
      />
    </template>
  </DsfrHeader>
  <DsfrNotice
    v-if="isLogged"
    type="info"
    :title="$t('header.notice.title')"
  >
    <template #desc>
      <i18n-t
        keypath="header.notice.desc"
        tag="span"
      >
        <template #articleLink>
          <a
            href="https://grist.numerique.gouv.fr/o/docs/rVja5acFwanx/Glossaire-MI/p/2"
            target="_blank"
            rel="noopener noreferrer"
            >{{ $t('header.notice.article-link-text') }}</a
          >
        </template>
        <template #formLink>
          <a
            href="https://grist.numerique.gouv.fr/o/docs/forms/3ceLBDoSMPmT4ScMosbJWd/4"
            target="_blank"
            rel="noopener noreferrer"
            >{{ $t('header.notice.form-link-text') }}</a
          >
        </template>
      </i18n-t>
    </template>
  </DsfrNotice>
</template>

<script setup lang="ts">
import type { DsfrHeaderProps } from '@gouvminint/vue-dsfr';
import { useI18n } from 'vue-i18n';
import { useAuth } from '../sign-in/use-auth';
import { confirmLeaveIfUploading } from '@/composables/use-confirm-leave';
import { computed } from 'vue';

const logoText = computed(() => [t('header.logo.text1'), t('header.logo.text2')]);
const { t } = useI18n();

const { signOut, isLogged } = inject('auth') as ReturnType<typeof useAuth>;

const whenLoggedLinks: DsfrHeaderProps['quickLinks'] = [
  {
    label: t('header.links.useful-tips'),
    icon: 'fr-icon-info-line',
    to: 'https://mirai.interieur.gouv.fr/outils-mirai/compte-rendu/bonnes-pratiques-fcr/',
    target: '_blank',
  },
  {
    label: t('header.links.sign-out'),
    icon: 'fr-icon-logout-box-r-line',
    button: true,
    onClick: async () => {
      if (await confirmLeaveIfUploading()) {
        signOut();
      }
    },
  },
];

const whenNotLoggedLinks: DsfrHeaderProps['quickLinks'] = [
  {
    label: t('header.links.sign-in'),
    to: '/',
    icon: 'ri-login-box-line',
  },
];

const quickLinks = computed<DsfrHeaderProps['quickLinks']>(() => {
  if (isLogged.value) {
    return whenLoggedLinks;
  } else {
    return whenNotLoggedLinks;
  }
});

function redirectTo(url: string): void {
  window.open(url, '_blank', 'noopener, noreferrer');
}
</script>

<style scoped>
:deep(.fr-badge) {
  background-color: #e8edff;
  color: #0063cb;
}

:deep(.fr-accordion__btn[aria-expanded='true']) {
  background-color: var(--background-open-blue-france);
  color: var(--background-action-high-blue-france);
}

:deep(.fr-accordion__btn[aria-expanded='true']:hover) {
  background-color: var(--background-open-blue-france-hover);
}

:deep(.fr-accordion__btn[aria-expanded='true']):active {
  background-color: var(--background-open-blue-france-active);
}

:deep(.fr-accordion__btn) {
  display: inline-flex;
  align-items: center;
}

/* Prevent the displaying of the icon for external links on the left of the buttons */
:deep(.fr-btn[target='_blank']::after) {
  display: none !important; /* enlève l'icône à droite */
}
</style>
