import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, screen } from '@testing-library/vue';
import { ref } from 'vue';
import LiveRecordingInProgress from '@/components/meeting/LiveRecordingInProgress.vue';
import { renderWithPlugins } from '@/vitest.setup';

const { session } = vi.hoisted(() => ({
  session: {
    availableDevices: { value: [] as { deviceId: string; label: string; groupId: string }[] },
    currentDeviceId: { value: '' },
    switchAudioDevice: vi.fn(),
  },
}));

vi.mock('@/composables/use-recording-session', () => ({
  useRecordingSession: () => ({
    time: { hours: ref(0), minutes: ref(0), seconds: ref(0) },
    isRecording: ref(true),
    isInactive: ref(false),
    isSendingLastAudioChunks: ref(false),
    availableDevices: session.availableDevices,
    currentDeviceId: session.currentDeviceId,
    audioInputLevel: ref(0),
    effectiveOffline: ref(false),
    statusLabel: ref('EN COURS'),
    switchAudioDevice: session.switchAudioDevice,
    pauseRecording: vi.fn(),
    resumeRecording: vi.fn(),
    stopRecording: vi.fn(),
  }),
}));

vi.mock('@/composables/use-leave-guard', () => ({ useLeaveGuard: vi.fn() }));
vi.mock('vue-final-modal', () => ({ useModal: () => ({ open: vi.fn() }) }));

function microphoneSelect() {
  return screen.getByLabelText(/Microphone/) as HTMLSelectElement;
}

describe('LiveRecordingInProgress', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    session.availableDevices.value = [
      { deviceId: 'mic-1', label: 'Micro intégré', groupId: 'g1' },
      { deviceId: 'usb-1', label: 'Casque USB', groupId: 'g2' },
    ];
    session.currentDeviceId.value = 'mic-1';
    session.switchAudioDevice.mockResolvedValue(undefined);
  });

  it('shows the microphone the recorder is actually using', () => {
    session.currentDeviceId.value = 'usb-1';

    renderWithPlugins(LiveRecordingInProgress, { props: { meetingId: 1 } });

    expect(microphoneSelect().value).toBe('usb-1');
  });

  it('offers every microphone the browser exposes', () => {
    renderWithPlugins(LiveRecordingInProgress, { props: { meetingId: 1 } });

    expect(screen.getByRole('option', { name: 'Micro intégré' })).toBeTruthy();
    expect(screen.getByRole('option', { name: 'Casque USB' })).toBeTruthy();
  });

  it('names the microphone even when the browser gives no label for it', () => {
    session.availableDevices.value = [{ deviceId: 'usb-1', label: '', groupId: 'g2' }];

    renderWithPlugins(LiveRecordingInProgress, { props: { meetingId: 1 } });

    expect(screen.getByRole('option', { name: /périphérique inconnu/ })).toBeTruthy();
  });

  it('moves the recording onto the microphone the user picks', async () => {
    session.switchAudioDevice.mockImplementation(async (deviceId: string) => {
      session.currentDeviceId.value = deviceId;
    });

    renderWithPlugins(LiveRecordingInProgress, { props: { meetingId: 1 } });
    await fireEvent.update(microphoneSelect(), 'usb-1');

    expect(session.switchAudioDevice).toHaveBeenCalledWith('usb-1');
    expect(microphoneSelect().value).toBe('usb-1');
  });

  it('goes back to the microphone still recording when the switch failed', async () => {
    // The session swallows the failure, so currentDeviceId never moves: without an
    // explicit realignment the select would keep showing a microphone nobody records on.
    renderWithPlugins(LiveRecordingInProgress, { props: { meetingId: 1 } });

    await fireEvent.update(microphoneSelect(), 'usb-1');

    expect(microphoneSelect().value).toBe('mic-1');
  });
});
