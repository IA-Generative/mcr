import HttpService, { API_PATHS } from '../http/http.service';
import type { UserDto } from '../users/users.service.types';
import type { SignInParams, SignInResponse } from './auth.service.types';

export async function signIn(params: SignInParams): Promise<SignInResponse> {
  const response = await HttpService.post(`${API_PATHS.AUTH}/sign-in`, params);
  return response.data;
}

export async function me(): Promise<UserDto> {
  const response = await HttpService.get(`${API_PATHS.AUTH}/me`);
  return response.data;
}
