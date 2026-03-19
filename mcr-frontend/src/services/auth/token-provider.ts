import { useKeycloak } from '@dsb-norge/vue-keycloak-js';
import { isInactive } from '@/composables/use-recorder';

type KeycloakInstance = NonNullable<ReturnType<typeof useKeycloak>['keycloak']>;

export class SessionExpiredError extends Error {
  constructor() {
    super('Session expired: refresh token is no longer valid');
    this.name = 'SessionExpiredError';
  }
}

const REFRESH_TOKEN_BUFFER_SECONDS = 30;
let loginRedirectAlreadyInProgress = false;

export function isRefreshTokenValid(keycloak: KeycloakInstance): boolean {
  const refreshTokenExpirationDate = keycloak.refreshTokenParsed?.exp;
  if (refreshTokenExpirationDate === undefined) {
    return false;
  }

  const nowInSeconds = Math.floor(Date.now() / 1000);
  const skew = keycloak.timeSkew ?? 0;
  return nowInSeconds - skew < refreshTokenExpirationDate - REFRESH_TOKEN_BUFFER_SECONDS;
}

export async function getValidToken(): Promise<string> {
  const { keycloak } = useKeycloak();
  if (!keycloak) throw new SessionExpiredError();

  if (!isRefreshTokenValid(keycloak)) {
    return handleDeadSession(keycloak);
  }

  await keycloak.updateToken();
  return keycloak.token!;
}

function handleDeadSession(keycloak: KeycloakInstance): never {
  const isRecordingActive = !isInactive.value;
  if (isRecordingActive) {
    throw new SessionExpiredError();
  }

  if (!loginRedirectAlreadyInProgress) {
    loginRedirectAlreadyInProgress = true;
    keycloak.login();
  }
  throw new SessionExpiredError();
}
