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

/* Prevent the displaying of the icon for external links on the left of the buttons */
:deep(.fr-btn[target='_blank']::after) {
  display: none !important; /* enlève l'icône à droite */
}

/* Recreate the icon for external links, but puts it on the right of the button */
:deep(.fr-btn[target='_blank']::before),
:deep(.fr-accordion__btn::before) {
  content: '';
  display: inline-block;
  width: 1rem;
  height: 1rem;
  margin-right: 0.5rem;
  flex-shrink: 0;

  background-color: currentColor;
  mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M14 3h7v7h-2V6.41l-9.29 9.3-1.42-1.42 9.3-9.29H14V3zM5 5h6V3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2v-6h-2v6H5V5z'/%3E%3C/svg%3E")
    no-repeat center / contain;
}
</style>
