// Tous les CSS tiers (DSFR, vue-final-modal, vue-dsfr) sont importés depuis main.css
// pour pouvoir les placer dans une cascade layer — voir le commentaire en tête du fichier.
import '@/main.css';

import { createApp } from 'vue';
import App from '@/App.vue';

import router from '@/router/index';

import { VueQueryPlugin } from '@tanstack/vue-query';

import { i18n } from '@/plugins/i18n';
import { createPinia } from 'pinia';
import { vueQueryPluginOptions } from '@/plugins/vue-query';
import { keycloakOptions } from '@/services/auth/keycloak';
import VueKeycloak from '@dsb-norge/vue-keycloak-js';
import { createVfm } from 'vue-final-modal';
import { initSentry } from '@/services/observability/sentry';
import { useUnleash } from '@/composables/use-unleash.ts';

const app = createApp(App);
const vfm = createVfm();

initSentry(app);

useUnleash();

app
  .use(createPinia())
  .use(i18n)
  .use(VueQueryPlugin, vueQueryPluginOptions)
  .use(vfm)
  .use(VueKeycloak, {
    ...keycloakOptions,
    onReady: () => {
      // Init the router after the keycloak is ready, to remove keycloak query params from the url
      const routerPlugin = router();
      app.use(routerPlugin);
      app.mount('#app');
    },
  });
