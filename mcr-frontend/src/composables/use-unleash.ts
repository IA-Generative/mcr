import { UnleashClient } from 'unleash-proxy-client';

let client: UnleashClient | null = null;
let started = false;

function initUnleash() {
  const url = (window as any).VITE_UNLEASH_URL || import.meta.env.VITE_UNLEASH_URL;
  const clientKey =
    (window as any).VITE_UNLEASH_CLIENT_KEY || import.meta.env.VITE_UNLEASH_CLIENT_KEY;

  if (!url || !clientKey) {
    throw new Error('Missing VITE_UNLEASH_URL or VITE_UNLEASH_CLIENT_KEY');
  }

  return new UnleashClient({
    url,
    clientKey,
    appName: 'mcr-frontend',
    refreshInterval: 15,
  });
}

export function useUnleash(): UnleashClient {
  if (!client) {
    client = initUnleash();
  }

  if (!started) {
    client.start();
    started = true;
  }

  return client!;
}
