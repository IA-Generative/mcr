const STORAGE_KEY_PREFIX = 'mcr-recording-progress';

export interface RecordingProgress {
  meetingId: number;
  chunkCount: number;
}

function getStorageKey(meetingId: number): string {
  return `${STORAGE_KEY_PREFIX}-${meetingId}`;
}

function loadRecordingProgress(meetingId: number): number | null {
  try {
    const key = getStorageKey(meetingId);
    const stored = localStorage.getItem(key);

    if (!stored) {
      return null;
    }

    const progress: RecordingProgress = JSON.parse(stored);

    if (!validateDataShape(progress)) {
      clearRecordingProgress(meetingId);
    }

    return progress.chunkCount;
  } catch (error) {
    console.error('[Recording Progress] Error loading progress:', error);
    return null;
  }
}

function validateDataShape(progress: RecordingProgress) {
  // Validate structure - A mettre dans un helper
  if (typeof progress.meetingId !== 'number' || typeof progress.chunkCount !== 'number') {
    console.warn(`[Recording Progress] Invalid data structure`);
    return false;
  }

  return true;
}

function saveRecordingProgress(meetingId: number, chunkCount: number): void {
  try {
    const key = getStorageKey(meetingId);
    const progress: RecordingProgress = {
      meetingId,
      chunkCount,
    };

    localStorage.setItem(key, JSON.stringify(progress));
  } catch (error) {
    console.error('[Recording Progress] Error saving progress:', error);
  }
}

function clearRecordingProgress(meetingId: number): void {
  try {
    const key = getStorageKey(meetingId);
    localStorage.removeItem(key);
  } catch (error) {
    console.error('[Recording Progress] Error clearing progress:', error);
  }
}

export function useLocalStorageRecording() {
  return {
    loadRecordingProgress,
    saveRecordingProgress,
    clearRecordingProgress,
  };
}
