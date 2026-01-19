export enum UserRole {
  USER = 'USER',
  ADMIN = 'ADMIN',
}

type UserRoleValues = keyof typeof UserRole;

export type UserDto = {
  keycloak_uuid: string;
  id: number;
  first_name: string;
  last_name: string;
  entity_name: string;
  email: string;
  role: UserRoleValues;
};

export type AddUserDto = Omit<UserDto, 'id' | 'keycloak_uuid'> & { password: string };
export type UpdateUserDto = Omit<AddUserDto, 'password'> & { password?: string };
