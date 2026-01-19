export const TRANSCRIPTION_WAITING_TIME_POLLING_INTERVAL = 60 * 1000; // 1 minute
export const PART_SIZE = 50 * 1024 * 1024; // 50Mo
export const MAX_RETRIES = 5;
export const BASE_BACKOFF_MS = 1000; // 1 second
export const MAX_DELAY = 30_000; // 30 seconds

export const getTranscriptionQueueWarningThreshold = (): number => {
  return Number(
    (window as any).APP_CONFIG?.VITE_TRANSCRIPTION_QUEUE_WARNING_THRESHOLD ||
      (window as any).VITE_TRANSCRIPTION_QUEUE_WARNING_THRESHOLD ||
      import.meta.env.VITE_TRANSCRIPTION_QUEUE_WARNING_THRESHOLD ||
      '1440',
  );
};

export const TRANSCRIPTION_QUEUE_WARNING_THRESHOLD = getTranscriptionQueueWarningThreshold();

export const config = {
  get transcriptionQueueWarningThreshold() {
    return getTranscriptionQueueWarningThreshold();
  },
};

export const getRetryDelay = (attemptIndex: number): number => {
  return BASE_BACKOFF_MS * Math.pow(2, attemptIndex - 1);
};
