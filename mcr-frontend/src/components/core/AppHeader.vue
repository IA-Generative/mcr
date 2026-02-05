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
            icon: 'fr-icon-message-2-line',
            onClick: () => redirectTo('https://chat.mirai.interieur.gouv.fr/'),
          },
          {
            label: $t('header.links.mirai-services.resumer'),
            icon: 'fr-icon-file-text-line',
            onClick: () =>
              redirectTo(
                'https://resume.mirai.interieur.gouv.fr/#state=16dda16b-b799-4db6-a767-ec323c1b2b01&session_state=88a7c723-8c3c-9952-a5f9-955f00b75ff0&iss=https%3A%2F%2Fsso.mirai.interieur.gouv.fr%2Frealms%2Fmirai&code=cf2bb656-eaa9-1962-fee6-ecf8ab37b533.88a7c723-8c3c-9952-a5f9-955f00b75ff0.1c2d0bc5-73c0-44fe-9bbe-578f1aed0edf',
              ),
          },
          {
            label: $t('header.links.mirai-services.ocr'),
            icon: 'fr-icon-camera-line',
            onClick: () =>
              redirectTo(
                'https://ocr.mirai.interieur.gouv.fr/#state=a9c89553-72af-4f9f-a431-b33bf7377d10&session_state=88a7c723-8c3c-9952-a5f9-955f00b75ff0&iss=https%3A%2F%2Fsso.mirai.interieur.gouv.fr%2Frealms%2Fmirai&code=75f7cb69-584b-53d1-e761-38b4aa89fb80.88a7c723-8c3c-9952-a5f9-955f00b75ff0.95354bda-e4df-44ec-8232-3d8bf5b822b8',
              ),
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
    label: t('header.links.user-guide'),
    icon: 'ri-question-line',
    to: '/fcr-guide-utilisateur.pdf',
    target: '_blank',
  },
  {
    label: t('header.links.sign-out'),
    icon: 'ri-logout-box-line',
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
</style>
