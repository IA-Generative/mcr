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
    v-if="isBetaEnabled"
    :title="$t('header.notice.title')"
  >
    <template #desc>
      <i18n-t
        keypath="header.notice.desc"
        tag="p"
      >
        <template #link>
          <a
            :href="URL_FORM_FEEDBACK"
            target="_blank"
          >
            {{ $t('header.notice.link') }}
          </a>
        </template>
      </i18n-t>
    </template>
  </DsfrNotice>
</template>

<script setup lang="ts">
import type { DsfrHeaderProps } from '@gouvminint/vue-dsfr';
import { useI18n } from 'vue-i18n';
import { useAuth } from '../sign-in/use-auth';
import { useUserStore } from '@/stores/useUserStore';
import { computed } from 'vue';
import { useFeatureFlag } from '@/composables/use-feature-flag.ts';

const logoText = computed(() => [t('header.logo.text1'), t('header.logo.text2')]);
const { t } = useI18n();

const userStore = useUserStore();
const { signOut } = inject('auth') as ReturnType<typeof useAuth>;

const isBetaEnabled = useFeatureFlag('beta');

const whenLoggedLinks: DsfrHeaderProps['quickLinks'] = [
  {
    label: t('header.links.useful-tips'),
    to: 'https://mirai.interieur.gouv.fr/outils-mirai/compte-rendu/bonnes-pratiques-fcr/',
    target: '_blank',
  },
  {
    label: t('header.links.sign-out'),
    icon: 'ri-logout-box-r-line',
    to: '/',
    onClick: () => {
      signOut();
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
  if (userStore.isLogged) {
    return whenLoggedLinks;
  } else {
    return whenNotLoggedLinks;
  }
});

function redirectTo(url: string): void {
  window.open(url, '_blank', 'noopener, noreferrer');
}

const URL_FORM_FEEDBACK =
  'https://grist.numerique.gouv.fr/o/miraigrist/forms/vvANEpRC3y67QtutV6JnJC/223';
</script>

<style scoped>
:deep() div.fr-notice__body > p {
  display: flex;
  flex-direction: column;
}

/* Breakpoint used in dsfr, close to tw md: */
@media (min-width: 48em) {
  :deep() div.fr-notice__body > p {
    display: flex;
    flex-direction: row;
  }

  :deep() .fr-notice__title {
    margin-bottom: 0;
  }
}

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

/* Prevent the displaying of the icon for external links on the left of the buttons */
:deep(.fr-btn[target='_blank']::after) {
  display: none !important; /* enlève l'icône à droite */
}
</style>
