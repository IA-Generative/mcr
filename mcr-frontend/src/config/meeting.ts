export const PART_SIZE = 50 * 1024 * 1024; // 50Mo
export const MAX_RETRIES = 5;
export const BASE_BACKOFF_MS = 1000; // 1 second
export const PUT_TIMEOUT_MS = 10 * 60 * 1000; // 10min

export const getRetryDelay = (attemptIndex: number): number => {
  return BASE_BACKOFF_MS * Math.pow(2, attemptIndex - 1);
};

export const MAX_DELAY_TO_FETCH_AUDIO = 7;
export const MAX_DELAY_TO_FETCH_DELIVERABLE = 30;
export const DELAY_TO_SHOW_ALERT = 20;
