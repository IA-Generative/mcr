import type { AxiosInstance } from 'axios';
import { setTokenForCurrentRequestConfig } from './http.utils';
import { getValidToken } from '@/services/auth/token-provider';

export function refreshTokenOnRequest(HttpService: AxiosInstance) {
  HttpService.interceptors.request.use(
    async (config) => {
      const token = await getValidToken();
      setTokenForCurrentRequestConfig(config, token);
      return config;
    },
    (error) => Promise.reject(error),
  );
}
