import axios from 'axios';
import { refreshTokenOnRequest } from './http.interceptors';
import { config } from '@/config/env';

export const API_URL = config.apiBaseUrl;

export enum API_PATHS {
  MEETINGS = 'meetings',
  MEMBERS = 'members',
  USERS = 'users',
  TRANSCRIPTIONS = 'transcriptions',
  AUTH = 'auth',
  LOOKUP = 'lookup',
  FEEDBACKS = 'feedbacks',
  DELIVERABLES = 'deliverables',
}

const HttpService = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

refreshTokenOnRequest(HttpService);

export default HttpService;
