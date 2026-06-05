import type { VueKeycloakOptions } from '@dsb-norge/vue-keycloak-js';
import { config } from '@/config/env';

export const keycloakOptions: VueKeycloakOptions = {
  config: {
    url: config.keycloak.url,
    realm: config.keycloak.realm,
    clientId: config.keycloak.clientId,
  },
  init: {
    onLoad: 'login-required',
    checkLoginIframe: false,
  },
  autoRefreshToken: false,
};
