import useToaster from '@/composables/use-toaster';
import { me } from '@/services/auth/auth.service';
import HttpService from '@/services/http/http.service';
import { useUserStore } from '@/stores/useUserStore';
import { useKeycloak } from '@dsb-norge/vue-keycloak-js';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { ROUTES } from '@/router/routes';
import { is401Error, is403Error } from '@/services/http/http.utils';
import { useQuery } from '@tanstack/vue-query';
import { isNewError, isNewUser } from '@/utils/auth';

export function useAuth() {
  const toaster = useToaster();
  const router = useRouter();
  const { t } = useI18n();
  const userStore = useUserStore();
  const { keycloak } = useKeycloak();
  const isLoading = ref(false);
  const currentUserQuery = useQuery({
    queryKey: ['user'],
    queryFn: me,
  });

  watch(
    () => currentUserQuery.data.value,
    (newUser, oldUser) => {
      if (isNewUser(newUser, oldUser)) {
        userStore.setUser(newUser ?? null);
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
        if (is401Error(newError) || is403Error(newError)) {
          toaster.addErrorMessage(t('error.default'));
          router.push(ROUTES.NOT_TESTER.path);
          userStore.setUser(null);
          return;
        } else {
          toaster.addErrorMessage(t('error.default'));
          router.push(ROUTES.LOGIN_ERROR.path);
          return;
        }
      }
    },
  );

  function signOut() {
    keycloak?.logout();
    delete HttpService.defaults.headers.common.Authorization;
    userStore.setUser(null);
  }

  return {
    signOut,
    currentUserQuery,
    isLoading,
  };
}
