import { useKeycloak } from '@dsb-norge/vue-keycloak-js';
import type { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { setTokenForCurrentRequestConfig } from './http.utils';

export function refreshTokenOnRequest(HttpService: AxiosInstance) {
  // Refresh token on request if it expires in the next 5 seconds
  HttpService.interceptors.request.use(
    async (config) => {
      try {
        await refreshTokenForCurrentAndFollowingRequests(config);
      } catch (error) {
        const { keycloak } = useKeycloak();
        if (!keycloak?.token || keycloak.isTokenExpired(0)) {
          return Promise.reject(error);
        }
        setTokenForCurrentRequestConfig(config, keycloak.token);
      }
      return config;
    },
    (error) => Promise.reject(error),
  );
}

async function refreshTokenForCurrentAndFollowingRequests(
  config: InternalAxiosRequestConfig,
  minValidity?: number,
) {
  const keycloakInstance = useKeycloak().keycloak;
  if (keycloakInstance === undefined) {
    return false;
  }

  const refreshed = await keycloakInstance.updateToken(minValidity);
  if (refreshed) {
    console.log('[interceptor] Token was refreshed by interceptor (auto-refresh missed it)');
  }
  const token = keycloakInstance.token;

  if (token) {
    setTokenForCurrentRequestConfig(config, keycloakInstance.token);
  }
}
