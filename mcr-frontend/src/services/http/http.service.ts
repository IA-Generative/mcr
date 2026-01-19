import axios from 'axios';
import { refreshTokenOnRequest } from './http.interceptors';

export const API_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export enum API_PATHS {
  MEETINGS = 'meetings',
  MEMBERS = 'members',
  USERS = 'users',
  TRANSCRIPTIONS = 'transcriptions',
  AUTH = 'auth',
  LOOKUP = 'lookup',
}

const HttpService = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

refreshTokenOnRequest(HttpService);

export default HttpService;
