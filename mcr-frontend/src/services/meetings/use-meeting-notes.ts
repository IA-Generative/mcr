import { ref, onUnmounted } from 'vue';
import { useDebounceFn } from '@vueuse/core';
import throttle from 'lodash.throttle';
import { useMeetings } from './use-meeting';

export type SyncStatus = 'idle' | 'pending' | 'saved';

const LOCALSTORAGE_DEBOUNCE_MS = 500; // 0.5 seconds
const API_THROTTLE_MS = 5000; // 5 seconds

export function useMeetingNotes(meetingId: number, serverNotes: string | null) {
  const localStorageKey = `meeting-notes-${meetingId}`;
  const savedLocally = localStorage.getItem(localStorageKey);

  const note = ref<string>(savedLocally ?? serverNotes ?? '');
  const syncStatus = ref<SyncStatus>('idle');

  const { updateNotesMutation } = useMeetings();
  const { mutateAsync } = updateNotesMutation();

  const debouncedSaveToLocalStorage = useDebounceFn(() => {
    localStorage.setItem(localStorageKey, note.value);
    syncStatus.value = 'saved';
  }, LOCALSTORAGE_DEBOUNCE_MS);

  const doSaveToServer = async () => {
    await mutateAsync({ id: meetingId, notes: note.value });
    localStorage.removeItem(localStorageKey);
  };

  const throttledSaveToServer = throttle(doSaveToServer, API_THROTTLE_MS, {
    leading: true,
    trailing: true,
  });

  function onUpdate(newValue: string) {
    note.value = newValue;
    syncStatus.value = 'pending';
    debouncedSaveToLocalStorage();
    throttledSaveToServer();
  }

  onUnmounted(() => {
    throttledSaveToServer.flush();
  });

  return { note, syncStatus, onUpdate };
}
