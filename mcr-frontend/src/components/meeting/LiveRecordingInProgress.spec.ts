import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/vue';
import { ref } from 'vue';
import LiveRecordingInProgress from '@/components/meeting/LiveRecordingInProgress.vue';
import { renderWithPlugins } from '@/vitest.setup';

const { session } = vi.hoisted(() => ({
  session: {
    availableDevices: { value: [] as { deviceId: string; label: string; groupId: string }[] },
    currentDeviceId: { value: '' },
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
    pauseRecording: vi.fn(),
    resumeRecording: vi.fn(),
    stopRecording: vi.fn(),
  }),
}));

vi.mock('@/composables/use-leave-guard', () => ({ useLeaveGuard: vi.fn() }));
vi.mock('vue-final-modal', () => ({ useModal: () => ({ open: vi.fn() }) }));

describe('LiveRecordingInProgress', () => {
  beforeEach(() => {
    session.availableDevices.value = [];
    session.currentDeviceId.value = '';
  });

  it('shows the microphone the recorder is actually using', () => {
    session.availableDevices.value = [
      { deviceId: 'mic-1', label: 'Micro intégré', groupId: 'g1' },
      { deviceId: 'usb-1', label: 'Casque USB', groupId: 'g2' },
    ];
    session.currentDeviceId.value = 'usb-1';

    renderWithPlugins(LiveRecordingInProgress, { props: { meetingId: 1 } });

    expect(screen.getByText(/Casque USB/)).toBeTruthy();
  });

  it('names the microphone even when the browser gives no label for it', () => {
    session.availableDevices.value = [{ deviceId: 'usb-1', label: '', groupId: 'g2' }];
    session.currentDeviceId.value = 'usb-1';

    renderWithPlugins(LiveRecordingInProgress, { props: { meetingId: 1 } });

    expect(screen.getByText(/périphérique inconnu/)).toBeTruthy();
  });

  it('names the microphone even when it is not in the list any more', () => {
    session.availableDevices.value = [{ deviceId: 'mic-1', label: 'Micro intégré', groupId: 'g1' }];
    session.currentDeviceId.value = 'usb-1';

    renderWithPlugins(LiveRecordingInProgress, { props: { meetingId: 1 } });

    expect(screen.getByText(/périphérique inconnu/)).toBeTruthy();
  });
});
