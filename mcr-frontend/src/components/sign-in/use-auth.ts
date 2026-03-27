import useToaster from '@/composables/use-toaster';
import { me } from '@/services/auth/auth.service';
import HttpService from '@/services/http/http.service';
import { UserRole, type UserDto } from '@/services/users/users.service.types';
import { useKeycloak } from '@dsb-norge/vue-keycloak-js';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { ROUTES } from '@/router/routes';
import { useQuery, useQueryClient } from '@tanstack/vue-query';
import { isNewError, isNewUser } from '@/utils/auth';
import type { Nullable } from '@/utils/types';

export function useAuth() {
  const toaster = useToaster();
  const router = useRouter();
  const { t } = useI18n();
  const { keycloak } = useKeycloak();
  const queryClient = useQueryClient();
  const currentUserQuery = useQuery({
    queryKey: ['user'],
    queryFn: me,
    refetchOnReconnect: false,
  });

  const currentUser = computed<Nullable<UserDto>>(() => currentUserQuery.data.value ?? null);
  const isLogged = computed(() => !!currentUser.value?.id);
  const isAdmin = computed(() => currentUser.value?.role === UserRole.ADMIN);

  watch(
    () => currentUserQuery.data.value,
    (newUser, oldUser) => {
      if (isNewUser(newUser, oldUser)) {
        toaster.addSuccessMessage(
          `${t('sign-in.connected-as')} ${newUser?.first_name} ${newUser?.last_name}`,
        );
      }
    },
  );

  watch(
    () => currentUserQuery.error.value,
    (newError, oldError) => {
      if (isNewError(newError, oldError)) {
        toaster.addErrorMessage(t('error.default'));
        router.push(ROUTES.LOGIN_ERROR.path);
        return;
      }
    },
  );

  function signOut() {
    keycloak?.logout();
    delete HttpService.defaults.headers.common.Authorization;
    queryClient.setQueryData(['user'], null);
  }

  return {
    signOut,
    currentUserQuery,
    currentUser,
    isLogged,
    isAdmin,
  };
}
