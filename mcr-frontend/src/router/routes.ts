import type { RouteRecordRaw } from 'vue-router';
// import Home from '@/views/HomePage.vue';
import NotFoundPage from '@/views/errors/NotFoundPage.vue';
import NotBetaTesterPage from '@/views/errors/NotBetaTesterPage.vue';
import LoginErrorPage from '@/views/errors/LoginErrorPage.vue';
import MeetingListPage from '@/views/meeting/MeetingListPage.vue';
import MeetingPage from '@/views/meeting/MeetingPage.vue';

export enum ROUTE_KEY {
  HOME = 'HOME',
  MEETINGS = 'MEETINGS',
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
