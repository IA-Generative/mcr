import '@gouvfr/dsfr/dist/core/core.main.min.css'; // Le CSS minimal du DSFR
import '@gouvfr/dsfr/dist/component/component.main.min.css'; // Styles de tous les composants du DSFR
import '@gouvfr/dsfr/dist/utility/utility.main.min.css'; // Classes utilitaires: les composants de VueDsfr en ont besoin
import '@gouvfr/dsfr/dist/scheme/scheme.min.css'; // Facultatif: Si les thèmes sont utilisés (thème sombre, thème clair)
import 'vue-final-modal/style.css'; // Small CSS bundle required for vfm, all styles are prefixed with `.vfm-`
import '@gouvminint/vue-dsfr/styles'; // Les styles propres aux composants de VueDsfr
import '@/main.css';

import { createApp } from 'vue';
import App from '@/App.vue';

import router from '@/router/index';

import { VueQueryPlugin } from '@tanstack/vue-query';

import { i18n } from '@/plugins/i18n';
import { vueQueryPluginOptions } from '@/plugins/vue-query';
import { keycloakOptions } from '@/services/auth/keycloak';
import VueKeycloak from '@dsb-norge/vue-keycloak-js';
import { createVfm } from 'vue-final-modal';
import * as Sentry from '@sentry/vue';
import VueMatomo from 'vue-matomo';
import { useUnleash } from '@/composables/use-unleash.ts';
import { config } from '@/config/env';

const app = createApp(App);
const vfm = createVfm();

if (config.sentry.dsn) {
  Sentry.init({
    app,
    dsn: config.sentry.dsn,
    sendDefaultPii: true,
    environment: config.envMode,
    enableLogs: true,
    integrations: [
      Sentry.consoleLoggingIntegration({
        levels: ['info', 'warn', 'error'],
      }),
    ],
    tracesSampleRate: 1.0,
  });
}

useUnleash();

app
  .use(i18n)
  .use(VueQueryPlugin, vueQueryPluginOptions)
  .use(vfm)
  .use(VueKeycloak, {
    ...keycloakOptions,
    onReady: (keycloak) => {
      // Init the router after the keycloak is ready, to remove keycloak query params from the url
      const routerPlugin = router();
      app.use(routerPlugin);

      if (config.matomo.host && config.matomo.siteId) {
        app.use(VueMatomo, {
          host: config.matomo.host,
          siteId: Number(config.matomo.siteId),
          router: routerPlugin,
          // Load tracker + endpoint same-origin so they pass the app's COEP
          // (require-corp) isolation; a reverse proxy forwards /matomo.* to the
          // Matomo host (vite server.proxy in dev, nginx in prod). Decided 2026-06-04.
          trackerScriptUrl: '/matomo.js',
          trackerUrl: '/matomo.php',
          // Cookieless tracking keeps Matomo within the CNIL consent exemption for
          // public-sector sites, so no cookie banner is required. Decided 2026-06-04.
          disableCookies: true,
          enableLinkTracking: true,
          userId: keycloak.subject, // pseudonymous Keycloak `sub`, never PII
        });
      }

      app.mount('#app');
    },
  });
