import { t } from '@/plugins/i18n';
import yup from '@/config/yup';

export type SignInField = {
  username: string;
  password: string;
};

export const SignInSchema: yup.Schema<SignInField> = yup.object({
  username: yup.string().required().email().label(t('sign-in.username')),
  password: yup.string().required().label(t('sign-in.password')),
});
