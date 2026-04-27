import type { RouteRecordRaw } from 'vue-router';
import NotFoundPage from '@/views/errors/NotFoundPage.vue';
import NotBetaTesterPage from '@/views/errors/NotBetaTesterPage.vue';
import LoginErrorPage from '@/views/errors/LoginErrorPage.vue';
import MeetingPage from '@/views/meeting/MeetingPage.vue';
import MeetingListPage from '@/views/meeting/MeetingListPage.vue';
import MeetingPageV2 from '@/views/meeting/MeetingPageV2.vue';

export enum ROUTE_KEY {
  HOME = 'HOME',
  MEETINGS = 'MEETINGS',
  MEETINGS_V2 = 'MEETINGS_V2',
  NOT_FOUND = 'NOT_FOUND',
  NOT_TESTER = 'NOT_TESTER',
  LOGIN_ERROR = 'LOGIN_ERROR',
}

export const ROUTES: Record<ROUTE_KEY, RouteRecordRaw> = {
  [ROUTE_KEY.HOME]: {
    path: '/',
    name: 'Home',
    redirect: {
      path: '/meetings',
    },
  },

  [ROUTE_KEY.MEETINGS_V2]: {
    path: '/v2/meetings',
    meta: { requireAuth: true, featureFlag: 'ux-v2' },
    children: [
      { path: ':id(\\d+)', component: MeetingPageV2, name: 'MeetingPageV2', props: true },
      { path: '', component: MeetingListPage, name: 'MeetingList' },
    ],
  },

  [ROUTE_KEY.MEETINGS]: {
    path: '/meetings',
    meta: { requireAuth: true },
    children: [
      { path: ':id(\\d+)', component: MeetingPage, name: 'MeetingPage', props: true },
      { path: '', component: MeetingListPage, name: 'MeetingList' },
    ],
  },
  [ROUTE_KEY.NOT_TESTER]: {
    path: '/non-tester',
    name: 'NotBetaTester',
    component: NotBetaTesterPage,
  },
  [ROUTE_KEY.NOT_FOUND]: {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: NotFoundPage,
  },
  [ROUTE_KEY.LOGIN_ERROR]: {
    path: '/login-error',
    name: 'LoginError',
    component: LoginErrorPage,
  },
};
