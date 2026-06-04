import { UnleashClient } from 'unleash-proxy-client';
import { config } from '@/config/env';

let client: UnleashClient | null = null;
let started = false;

function initUnleash() {
  return new UnleashClient({
    url: config.unleash.url,
    clientKey: config.unleash.clientKey,
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
