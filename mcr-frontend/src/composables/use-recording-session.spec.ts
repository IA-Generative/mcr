import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, ref } from 'vue';
import { render } from '@testing-library/vue';
import type { AudioDeviceInfo, RecordingStartContext } from '@/composables/use-recorder';

const { recorder, toaster, monitor } = vi.hoisted(() => ({
  recorder: {
    currentAudioId: { value: '' as string | undefined },
    listAudioInputDevices: vi.fn(),
    startRecording: vi.fn(),
  },
  toaster: {
    addInfoMessage: vi.fn(),
    addWarningMessage: vi.fn(),
    addErrorMessage: vi.fn(),
  },
  monitor: {
    attach: vi.fn(),
  },
}));

vi.mock('@/composables/use-recorder', () => ({
  useRecorder: () => ({
    time: { hours: ref(0), minutes: ref(0), seconds: ref(0) },
    isRecording: ref(true),
    isInactive: ref(false),
    currentAudioId: recorder.currentAudioId,
    listAudioInputDevices: recorder.listAudioInputDevices,
    startRecording: recorder.startRecording,
    resumeRecording: vi.fn(),
    stopRecording: vi.fn(),
    pauseRecording: vi.fn(),
  }),
}));

vi.mock('@/composables/use-recording-monitor', () => ({
  SILENCE_MESSAGES: {},
  useRecordingMonitor: () => ({
    audioInputLevel: ref(0),
    attach: monitor.attach,
    silenceVerdict: () => ({ isSilent: false, cause: 'none', stats: {} }),
  }),
}));

vi.mock('@/composables/use-toaster', () => ({ default: () => toaster }));

vi.mock('@/composables/use-network-status', () => ({
  useNetworkStatus: () => ({ isOnline: ref(true) }),
}));

vi.mock('@/composables/use-audio-chunk-store', () => ({
  useAudioChunkStore: () => ({
    getChunkCountForMeeting: vi.fn().mockResolvedValue(0),
    getPendingChunksForMeeting: vi.fn().mockResolvedValue([]),
  }),
}));

vi.mock('@/composables/use-chunk-upload', () => ({
  useChunkUpload: () => ({
    saveAndEnqueueUpload: vi.fn(),
    uploadPendingFromIdb: vi.fn(),
    waitForAllUploads: vi.fn(),
  }),
}));

vi.mock('@/composables/use-audio-chunk-cleanup', () => ({
  useAudioChunkCleanup: () => ({ cleanupMeetingChunks: vi.fn() }),
}));

vi.mock('@/services/meetings/use-meeting', () => ({
  useMeetings: () => ({
    startTranscriptionMutation: () => ({ mutate: vi.fn() }),
    getMeetingQuery: () => ({ data: ref(undefined) }),
  }),
}));

import { useRecordingSession } from './use-recording-session';

const deviceChangeListeners = new Set<() => unknown>();

function device(deviceId: string, label = ''): AudioDeviceInfo {
  return { deviceId, label, groupId: 'group' };
}

type Session = ReturnType<typeof useRecordingSession>;

function mountSession() {
  let session!: Session;
  const Host = defineComponent({
    setup() {
      session = useRecordingSession(1);
      return () => null;
    },
  });
  const { unmount } = render(Host);
  return { session: () => session, unmount };
}

async function flush() {
  await new Promise((resolve) => setTimeout(resolve, 0));
}

async function emitDeviceChange() {
  for (const listener of [...deviceChangeListeners]) await listener();
  await flush();
}

function startRecordingWith(devices: AudioDeviceInfo[]) {
  const ctx = {
    stream: { getAudioTracks: () => [] },
    recorder: {},
    requestedDeviceId: null,
    availableDevices: devices,
  } as unknown as RecordingStartContext;
  const options = recorder.startRecording.mock.calls.at(-1)?.[0];
  options?.onRecordingStart?.(ctx);
}

describe('useRecordingSession devices', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    deviceChangeListeners.clear();
    recorder.currentAudioId.value = '';
    recorder.listAudioInputDevices.mockResolvedValue([]);
    recorder.startRecording.mockResolvedValue(undefined);

    Object.defineProperty(navigator, 'mediaDevices', {
      value: {
        addEventListener: (type: string, listener: () => unknown) => {
          if (type === 'devicechange') deviceChangeListeners.add(listener);
        },
        removeEventListener: (_type: string, listener: () => unknown) => {
          deviceChangeListeners.delete(listener);
        },
      },
      writable: true,
      configurable: true,
    });
  });

  it('offers the audio inputs to the screen as soon as the card opens', async () => {
    recorder.listAudioInputDevices.mockResolvedValue([device('mic-1', 'Micro intégré')]);

    const { session } = mountSession();
    await flush();

    expect(session().availableDevices.value).toEqual([device('mic-1', 'Micro intégré')]);
  });

  it('names the device the recorder is actually using', async () => {
    const { session } = mountSession();
    await flush();

    recorder.currentAudioId.value = 'mic-2';

    expect(session().currentDeviceId.value).toBe('mic-2');
  });

  it('keeps the screen in sync when a device is plugged in', async () => {
    const { session } = mountSession();
    await flush();
    startRecordingWith([device('mic-1', 'Micro intégré')]);

    recorder.listAudioInputDevices.mockResolvedValue([
      device('mic-1', 'Micro intégré'),
      device('usb-1', 'Casque USB'),
    ]);
    await emitDeviceChange();

    expect(session().availableDevices.value).toContainEqual(device('usb-1', 'Casque USB'));
  });

  it('stops refreshing the list once the card is gone', async () => {
    const { session, unmount } = mountSession();
    await flush();
    startRecordingWith([device('mic-1', 'Micro intégré')]);

    unmount();
    recorder.listAudioInputDevices.mockResolvedValue([device('usb-1', 'Casque USB')]);
    await emitDeviceChange();

    expect(session().availableDevices.value).toEqual([device('mic-1', 'Micro intégré')]);
  });

  it('shows no device rather than crashing when they cannot be listed', async () => {
    recorder.listAudioInputDevices.mockRejectedValue(new Error('permission denied'));

    const { session } = mountSession();
    await flush();

    expect(session().availableDevices.value).toEqual([]);
  });

  it('prefers the labelled list the recorder gets once the permission is granted', async () => {
    recorder.listAudioInputDevices.mockResolvedValue([device('mic-1', '')]);

    const { session } = mountSession();
    await flush();
    startRecordingWith([device('mic-1', 'Micro intégré')]);

    expect(session().availableDevices.value).toEqual([device('mic-1', 'Micro intégré')]);
  });

  it('tells the user which microphone has just been plugged in', async () => {
    const { session } = mountSession();
    await flush();
    startRecordingWith([device('mic-1', 'Micro intégré')]);

    recorder.listAudioInputDevices.mockResolvedValue([
      device('mic-1', 'Micro intégré'),
      device('usb-1', 'Casque USB'),
    ]);
    await emitDeviceChange();

    expect(toaster.addInfoMessage).toHaveBeenCalledWith(expect.stringContaining('Casque USB'));
    expect(session().currentDeviceId.value).toBe('');
  });

  it('tells the user which microphone has been unplugged', async () => {
    recorder.currentAudioId.value = 'mic-1';
    mountSession();
    await flush();
    startRecordingWith([device('mic-1', 'Micro intégré'), device('usb-1', 'Casque USB')]);

    recorder.listAudioInputDevices.mockResolvedValue([device('mic-1', 'Micro intégré')]);
    await emitDeviceChange();

    expect(toaster.addInfoMessage).toHaveBeenCalledWith(expect.stringContaining('Casque USB'));
    expect(toaster.addWarningMessage).not.toHaveBeenCalled();
  });

  it('warns the user when the microphone being recorded is unplugged', async () => {
    recorder.currentAudioId.value = 'usb-1';
    mountSession();
    await flush();
    startRecordingWith([device('mic-1', 'Micro intégré'), device('usb-1', 'Casque USB')]);

    recorder.listAudioInputDevices.mockResolvedValue([device('mic-1', 'Micro intégré')]);
    await emitDeviceChange();

    expect(toaster.addWarningMessage).toHaveBeenCalledWith(expect.stringContaining('Casque USB'));
    expect(toaster.addInfoMessage).not.toHaveBeenCalled();
  });

  it('blames only the recorded microphone when several are unplugged at once', async () => {
    recorder.currentAudioId.value = 'usb-1';
    mountSession();
    await flush();
    startRecordingWith([
      device('mic-1', 'Micro intégré'),
      device('usb-1', 'Casque USB'),
      device('bt-1', 'Oreillette Bluetooth'),
    ]);

    recorder.listAudioInputDevices.mockResolvedValue([device('mic-1', 'Micro intégré')]);
    await emitDeviceChange();

    expect(toaster.addWarningMessage).toHaveBeenCalledTimes(1);
    expect(toaster.addWarningMessage).toHaveBeenCalledWith(expect.stringContaining('Casque USB'));
    expect(toaster.addWarningMessage).not.toHaveBeenCalledWith(
      expect.stringContaining('Oreillette Bluetooth'),
    );
    expect(toaster.addInfoMessage).toHaveBeenCalledWith(
      expect.stringContaining('Oreillette Bluetooth'),
    );
  });

  it('names each microphone plugged in at once in its own message', async () => {
    const { session } = mountSession();
    await flush();
    startRecordingWith([device('mic-1', 'Micro intégré')]);

    recorder.listAudioInputDevices.mockResolvedValue([
      device('mic-1', 'Micro intégré'),
      device('usb-1', 'Casque USB'),
      device('bt-1', 'Oreillette Bluetooth'),
    ]);
    await emitDeviceChange();

    expect(toaster.addInfoMessage).toHaveBeenCalledWith(expect.stringContaining('Casque USB'));
    expect(toaster.addInfoMessage).toHaveBeenCalledWith(
      expect.stringContaining('Oreillette Bluetooth'),
    );
    expect(toaster.addInfoMessage).not.toHaveBeenCalledWith(
      expect.stringContaining('Casque USB, Oreillette Bluetooth'),
    );
    expect(session().currentDeviceId.value).toBe('');
  });

  it('announces nothing for the devices already there when the card opens', async () => {
    // Before the permission is granted the browser hides part of the list: the devices it then
    // reveals were already plugged in, and announcing them would fire at every card opening.
    recorder.listAudioInputDevices.mockResolvedValue([device('mic-1', '')]);

    mountSession();
    await flush();

    recorder.listAudioInputDevices.mockResolvedValue([
      device('mic-1', 'Micro intégré'),
      device('usb-1', 'Casque USB'),
    ]);
    await emitDeviceChange();
    startRecordingWith([device('mic-1', 'Micro intégré'), device('usb-1', 'Casque USB')]);
    await flush();

    expect(toaster.addInfoMessage).not.toHaveBeenCalled();
    expect(toaster.addWarningMessage).not.toHaveBeenCalled();
  });

  it('announces nothing when only the label of a device changes', async () => {
    mountSession();
    await flush();
    startRecordingWith([device('default', 'Micro intégré')]);

    recorder.listAudioInputDevices.mockResolvedValue([device('default', 'Default - Casque USB')]);
    await emitDeviceChange();

    expect(toaster.addInfoMessage).not.toHaveBeenCalled();
    expect(toaster.addWarningMessage).not.toHaveBeenCalled();
  });

  it('falls back to a readable name for a device the browser does not label', async () => {
    mountSession();
    await flush();
    startRecordingWith([device('mic-1', 'Micro intégré')]);

    recorder.listAudioInputDevices.mockResolvedValue([
      device('mic-1', 'Micro intégré'),
      device('usb-1', ''),
    ]);
    await emitDeviceChange();

    expect(toaster.addInfoMessage).toHaveBeenCalledWith(
      expect.stringContaining('périphérique inconnu'),
    );
  });
});
