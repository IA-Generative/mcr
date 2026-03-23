import { HttpStatusCode, type AxiosError, type InternalAxiosRequestConfig } from 'axios';

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
  return getStatusCode(error) === HttpStatusCode.Forbidden;
}

export function is404Error(error: unknown): boolean {
  return getStatusCode(error) === HttpStatusCode.NotFound;
}

function getStatusCode(error: unknown): number | undefined {
  if (error && typeof error === 'object' && 'response' in error) {
    return (error as AxiosError).response?.status;
  }
  return undefined;
}

const RETRYABLE_STATUS_CODES: ReadonlySet<HttpStatusCode> = new Set([
  HttpStatusCode.RequestTimeout,
  HttpStatusCode.InternalServerError,
  HttpStatusCode.BadGateway,
  HttpStatusCode.ServiceUnavailable,
  HttpStatusCode.GatewayTimeout,
  HttpStatusCode.InsufficientStorage,
]);

export function isRetryableError(error: unknown): boolean {
  const status = getStatusCode(error);
  if (status === undefined) return false;
  return RETRYABLE_STATUS_CODES.has(status);
}
