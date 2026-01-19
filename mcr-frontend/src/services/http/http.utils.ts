import type { AxiosError, InternalAxiosRequestConfig } from 'axios';

export function setTokenForCurrentRequestConfig(
  config: InternalAxiosRequestConfig,
  token?: string,
) {
  config.headers.Authorization = getFullAuthHeader(token);

  return config;
}

function getFullAuthHeader(token?: string) {
  return `Bearer ${token}`;
}

export function is403Error(error: unknown): boolean {
  return isStatusError(error, 403);
}

export function is404Error(error: unknown): boolean {
  return isStatusError(error, 404);
}

export function is401Error(error: unknown): boolean {
  return isStatusError(error, 401);
}

function isStatusError(error: unknown, status: number): boolean {
  if (error && typeof error === 'object' && 'response' in error) {
    const err = error as AxiosError;
    return err.response?.status === status;
  }
  return false;
}
