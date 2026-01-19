import type { VueKeycloakOptions } from '@dsb-norge/vue-keycloak-js';

export const keycloakOptions: VueKeycloakOptions = {
  config: {
    url: (window as any).VITE_KEYCLOAK_URL || import.meta.env.VITE_KEYCLOAK_URL,
    realm: (window as any).VITE_KEYCLOAK_REALM || import.meta.env.VITE_KEYCLOAK_REALM,
    clientId: (window as any).VITE_KEYCLOAK_CLIENT_ID || import.meta.env.VITE_KEYCLOAK_CLIENT_ID,
  },
  init: {
    onLoad: 'login-required',
    checkLoginIframe: false,
  },
};
