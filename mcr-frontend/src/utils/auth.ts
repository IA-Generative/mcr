import type { UserDto } from '@/services/users/users.service.types';

export function isNewError(newError: Error | null, oldError: Error | null) {
  return newError && !oldError;
}

export function isNewUser(newUser: UserDto | undefined, oldUser: UserDto | undefined) {
  return newUser && !oldUser;
}
