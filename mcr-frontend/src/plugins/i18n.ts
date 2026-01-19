import { createI18n } from 'vue-i18n';
import FR from '@/locales/fr.json';

export type LOCALE = 'fr';
export const SUPPORTED_LOCALES: LOCALE[] = ['fr'];

export type MessageSchema = typeof FR;

type Join<K, P> = K extends string | number
  ? P extends string | number
    ? `${K}.${P}`
    : never
  : never;

type NestedKeys<T> = {
  [K in keyof T & string]: T[K] extends Record<string, any> ? Join<K, NestedKeys<T[K]>> : K;
}[keyof T & string];

export type MessageKeys = NestedKeys<MessageSchema>;

export const i18n = createI18n<[MessageSchema], LOCALE>({
  locale: 'fr',
  messages: {
    fr: FR,
  },
});

export const t = i18n.global.t;
