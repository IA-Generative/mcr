import { UserRole, type UserDto } from '@/services/users/users.service.types';
import type { Nullable } from '@/utils/types';
import { defineStore } from 'pinia';

export const useUserStore = defineStore('user', () => {
  const currentUser = ref<Nullable<UserDto>>(null);

  const isLogged = computed(() => !!currentUser.value?.id);

  const isAdmin = computed(() => currentUser.value?.role === UserRole.ADMIN);

  function setUser(user: UserDto | null) {
    currentUser.value = user;
  }

  return {
    currentUser,
    setUser,
    isLogged,
    isAdmin,
  };
});
