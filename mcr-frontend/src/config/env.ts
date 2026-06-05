// Runtime configuration is injected onto `window` by /config.js at deploy time
// (see index.html); `import.meta.env` is the build-time fallback. This module is the
// single typed entry point for both sources

declare global {
  interface Window {
    ENV_MODE?: string;
    VITE_ENV_MODE?: string;
    VITE_API_BASE_URL?: string;
    VITE_SENTRY_FRONTEND_DSN?: string;
    VITE_KEYCLOAK_URL?: string;
    VITE_KEYCLOAK_REALM?: string;
    VITE_KEYCLOAK_CLIENT_ID?: string;
    VITE_UNLEASH_URL?: string;
    VITE_UNLEASH_CLIENT_KEY?: string;
    VITE_MATOMO_HOST?: string;
    VITE_MATOMO_SITE_ID?: string;
  }
}

const RUNTIME = window as unknown as Record<string, string | undefined>;
const BUILD = import.meta.env as unknown as Record<string, string | undefined>;
const isTest = import.meta.env.MODE === 'test'; // Vitest

function read(viteKey: string, windowKey: string = viteKey): string | undefined {
  return RUNTIME[windowKey] || BUILD[viteKey] || undefined;
}

function required(viteKey: string, windowKey: string = viteKey): string {
  const value = read(viteKey, windowKey);
  if (!value) {
    // Unit tests never inject these; returning '' keeps imports from throwing.
    if (isTest) return '';
    throw new Error(
      `[config] missing required env ${viteKey} (window.${windowKey} | import.meta.env.${viteKey})`,
    );
  }
  return value;
}

export const config = {
  envMode: read('VITE_ENV_MODE', 'ENV_MODE'),
  apiBaseUrl: read('VITE_API_BASE_URL') ?? '/api',
  keycloak: {
    url: required('VITE_KEYCLOAK_URL'),
    realm: required('VITE_KEYCLOAK_REALM'),
    clientId: required('VITE_KEYCLOAK_CLIENT_ID'),
  },
  unleash: {
    url: required('VITE_UNLEASH_URL'),
    clientKey: required('VITE_UNLEASH_CLIENT_KEY'),
  },
  sentry: {
    dsn: read('VITE_SENTRY_FRONTEND_DSN'),
  },
  matomo: {
    host: read('VITE_MATOMO_HOST'),
    siteId: read('VITE_MATOMO_SITE_ID'),
  },
} as const;
